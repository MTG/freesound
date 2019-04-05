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

import logging
import os
import shutil
import subprocess

from django.conf import settings

from utils.audioprocessing.processing import AudioProcessingException
from utils.audioprocessing.freesound_audio_processing import FreesoundAudioProcessorBase
from utils.filesystem import create_directories
from utils.mirror_files import copy_analysis_to_mirror_locations


logger = logging.getLogger("processing")


class FreesoundAudioAnalyzer(FreesoundAudioProcessorBase):

    def failure(self, message, error=None, failure_state="FA"):
        super(FreesoundAudioAnalyzer, self).failure(message, error)
        self.sound.set_analysis_state(failure_state)

    def analyze(self):

        try:
            # Get the path of the original sound and convert to PCM
            sound_path = self.get_sound_path()
            tmp_wavefile = self.convert_to_pcm(sound_path)

            # Check if filesize of the converted file
            if settings.MAX_FILESIZE_FOR_ANALYSIS is not None:
                if os.path.getsize(tmp_wavefile) > settings.MAX_FILESIZE_FOR_ANALYSIS:
                    self.failure('converted file is larger than %sMB and therefore it won\'t be analyzed.' %
                                 (int(settings.MAX_FILESIZE_FOR_ANALYSIS/1024/1024)), failure_state='SK')
                    return False

            # Create directories where to store analysis files and move them there
            statistics_path = self.sound.locations("analysis.statistics.path")
            frames_path = self.sound.locations("analysis.frames.path")
            create_directories(os.path.dirname(statistics_path))
            create_directories(os.path.dirname(frames_path))

            # Run Essentia's FreesoundExtractor analsyis
            essentia_dir = os.path.dirname(os.path.abspath(settings.ESSENTIA_EXECUTABLE))
            os.chdir(essentia_dir)
            exec_array = [settings.ESSENTIA_EXECUTABLE, tmp_wavefile,
                          os.path.join(self.tmp_directory, 'ess_%i' % self.sound.id)]
            if settings.ESSENTIA_PROFILE_FILE_PATH is not None:
                exec_array += [settings.ESSENTIA_PROFILE_FILE_PATH]

            p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            if p.returncode != 0:
                self.failure("essentia extractor returned an error\nstdout: %s \nstderr: %s" % (out, err))
                return False

            # Move essentia output files to analysis data directory
            if settings.ESSENTIA_PROFILE_FILE_PATH:
                # Never versions of FreesoundExtractor using profile file use a different naming convention
                shutil.move(os.path.join(self.tmp_directory, 'ess_%i' % self.sound.id), statistics_path)
                shutil.move(os.path.join(self.tmp_directory, 'ess_%i_frames' % self.sound.id), frames_path)
            else:
                shutil.move(os.path.join(self.tmp_directory, 'ess_%i_statistics.yaml' % self.sound.id), statistics_path)
                shutil.move(os.path.join(self.tmp_directory, 'ess_%i_frames.json' % self.sound.id), frames_path)

            self.log_info("created analysis files with FreesoundExtractor: %s, %s" % (statistics_path, frames_path))

            # Change sound analysis and similarity states
            self.sound.set_analysis_state('OK')
            self.sound.set_similarity_state('PE')  # Set similarity to PE so sound will get indexed to Gaia

        except AudioProcessingException as e:
            self.failure(e)
            return False
        except (Exception, OSError) as e:
            self.failure("unexpected error in analysis ", e)
            return False

        # Clean up temp files
        self.cleanup()

        # Copy analysis files to mirror locations
        copy_analysis_to_mirror_locations(self.sound)

        return True
