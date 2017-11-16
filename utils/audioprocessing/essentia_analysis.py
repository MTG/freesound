#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.conf import settings
import os, shutil, subprocess, signal, sys
from utils.mirror_files import copy_analysis_to_mirror_locations


def analyze(sound):
    FFMPEG_TIMEOUT = 3 * 60
    tmp_conv = False

    def  alarm_handler(signum, frame):
        raise Exception("timeout while waiting for ffmpeg")

    #TODO: refactor processing and analysis together
    def write_log(message):
        sys.stdout.write(str(message)+'\n')
        sys.stdout.flush()

    def failure(message, error=None, failure_state="FA"):
        sound.set_analysis_state(failure_state)
        logging_message = "Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s\n" + str(error)
        write_log(message)

    try:
        statistics_path = sound.locations("analysis.statistics.path")
        frames_path = sound.locations("analysis.frames.path")
        input_path = sound.locations('path')

        if not os.path.exists(input_path):
            failure('Could not find file with path %s'% input_path)
            return False

        if os.path.getsize(input_path) >100 * 1024 * 1024: #same as filesize_warning in sound model
            failure('File is larger than 100MB. Passing on it.', failure_state='SK')
            return False

        ext = os.path.splitext(input_path)[1]
        if ext in ['.wav', '.aiff', '.aifc', '.aif']:
            tmp_conv = True
            tmp_wav_path = '/tmp/conversion_%s.wav' % sound.id
            try:
                p = subprocess.Popen(['ffmpeg', '-y', '-i', input_path, '-acodec', 'pcm_s16le',
                                  '-ac', '1', '-ar', '44100', tmp_wav_path])
                signal.signal(signal.SIGALRM, alarm_handler)
                signal.alarm(FFMPEG_TIMEOUT)
                p.wait()
                signal.alarm(0)
            except Exception as e:
                failure("ffmpeg conversion failed ", e)
                return False
            input_path = tmp_wav_path
        tmp_ana_path = '/tmp/analysis_%s' % sound.id
        essentia_dir = os.path.dirname(os.path.abspath(settings.ESSENTIA_EXECUTABLE))
        os.chdir(essentia_dir)
        exec_array = [settings.ESSENTIA_EXECUTABLE, input_path, tmp_ana_path]

        try:
            p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_result = p.wait()
            if p_result != 0:
                output_std, output_err = p.communicate()
                failure( "Essentia extractor returned an error (%s) stdout:%s stderr: %s"%(p_result, output_std, output_err))
                return False
        except Exception as e:
            failure("Essentia extractor failed ", e)
            return False

        __create_dir(statistics_path)
        __create_dir(frames_path)
        shutil.move('%s_statistics.yaml' % tmp_ana_path, statistics_path)
        shutil.move('%s_frames.json' % tmp_ana_path, frames_path)
        #os.remove('%s.json' % tmp_ana_path)  # Current extractor does not produce the json file
        sound.set_analysis_state('OK')
        sound.set_similarity_state('PE')  # So sound gets reindexed in gaia
    except Exception as e:
        failure("Unexpected error in analysis ", e)
        return False
    finally:
        if tmp_conv:
            os.remove(tmp_wav_path)

    # Copy analysis and display files to mirror locations
    copy_analysis_to_mirror_locations(sound)
    return True


def __create_dir(path):
    dir_path = os.path.dirname(os.path.abspath(path))
    if not  os.path.exists(dir_path):
        os.makedirs(dir_path)
