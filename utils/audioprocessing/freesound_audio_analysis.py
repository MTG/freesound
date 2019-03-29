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

import errno
import logging
import os
import shutil
import subprocess
import sys
import tempfile

from django.conf import settings

import utils.audioprocessing.processing as audioprocessing
from utils.audioprocessing.processing import AudioProcessingException
from utils.mirror_files import copy_analysis_to_mirror_locations


logger = logging.getLogger("processing")


def analyze(sound):

    def write_log(message):
        sys.stdout.write(str(message) + '\n')
        sys.stdout.flush()
        logger.info("[%d] %i: %s" % (os.getpid(), sound.id, message))

    def create_directory(path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                # Directory already exists
                pass
            else:
                # Directory could not be created, raise exception
                raise

    def cleanup(files):
        success("cleaning up processing files: " + ", ".join(files))
        for filename in files:
            try:
                os.unlink(filename)
            except:
                pass

    def failure(message, error=None, failure_state="FA"):
        sound.set_analysis_state(failure_state)
        logging_message = "Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s\n" + str(error)
        write_log(message)
        cleanup(to_cleanup)

    def success(message):
        write_log('- ' + message)

    to_cleanup = []  # This will hold a list of files to cleanup after processing

    try:
        # Get the path of the original sound
        sound_path = sound.locations('path')
        if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
            sound_path = sound.locations('preview.LQ.mp3.path')

        if not os.path.exists(sound_path):
            failure('could not find file with path %s' % sound_path)
            return False

        if settings.MAX_FILESIZE_FOR_ANALYSIS is not None:
            if os.path.getsize(sound_path) > settings.MAX_FILESIZE_FOR_ANALYSIS:
                failure('file is larger than %sMB and therefore it won\'t be analyzed.' %
                        (int(settings.MAX_FILESIZE_FOR_ANALYSIS/1024/1024)), failure_state='SK')
                return False

        # Convert to PCM and save PCM version in `tmp_wavefile`
        try:
            tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
            audioprocessing.convert_using_ffmpeg(sound_path, tmp_wavefile, mono_out=True)
            to_cleanup.append(tmp_wavefile)
            success("converted to PCM: " + tmp_wavefile)

        except AudioProcessingException as e:
            failure("conversion to PCM failed", e)
            return False
        except IOError as e:
            # Could not create tmp file
            failure("could not create tmp_wavefile file", e)
            return False
        except Exception as e:
            failure("unhandled exception while converting to PCM", e)
            return False

        out_tmp_analysis_path = '/tmp/analysis_%s' % sound.id
        essentia_dir = os.path.dirname(os.path.abspath(settings.ESSENTIA_EXECUTABLE))
        os.chdir(essentia_dir)
        exec_array = [settings.ESSENTIA_EXECUTABLE, tmp_wavefile, out_tmp_analysis_path]

        try:
            p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_result = p.wait()
            if p_result != 0:
                output_std, output_err = p.communicate()
                failure("Essentia extractor returned an error (%s) stdout:%s stderr: %s"
                        % (p_result, output_std, output_err))
                return False
            to_cleanup.append(out_tmp_analysis_path)

        except Exception as e:
            failure("Essentia extractor failed ", e)
            return False

        # Create directories where to store analysis files and move them there
        statistics_path = sound.locations("analysis.statistics.path")
        frames_path = sound.locations("analysis.frames.path")
        create_directory(statistics_path)
        create_directory(frames_path)
        shutil.move('%s_statistics.yaml' % out_tmp_analysis_path, statistics_path)
        shutil.move('%s_frames.json' % out_tmp_analysis_path, frames_path)

        sound.set_analysis_state('OK')
        sound.set_similarity_state('PE')  # Set similarity to PE so sound will get indexed to Gaia

    except Exception as e:
        failure("Unexpected error in analysis ", e)
        return False
    except OSError:
        failure("could not create directory for statistics and/or frames")
        return False

    # Clean up temp files
    cleanup(to_cleanup)

    # Copy analysis files to mirror locations
    copy_analysis_to_mirror_locations(sound)

    return True
