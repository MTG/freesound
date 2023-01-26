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

from __future__ import absolute_import
from __future__ import division

from builtins import str
from past.utils import old_div
from builtins import object
import json
import os
import signal
import logging
import tempfile

from django.apps import apps
from django.conf import settings

from . import color_schemes
import utils.audioprocessing.processing as audioprocessing
from utils.audioprocessing.processing import AudioProcessingException
from utils.filesystem import create_directories, TemporaryDirectory
from utils.mirror_files import copy_previews_to_mirror_locations, copy_displays_to_mirror_locations
from utils.sound_upload import get_processing_before_describe_sound_folder

console_logger = logging.getLogger("console")


class WorkerException(Exception):
    """
    Exception raised by the worker if:
    i) the analysis/processing function takes longer than the timeout specified in settings.WORKER_TIMEOUT
    ii) the check for free disk space  before running the analysis/processing function fails
    """
    pass


def set_timeout_alarm(time, msg):
    """
    Sets a timeout alarm which raises a WorkerException after a number of seconds.
    :param float time: seconds until WorkerException is raised
    :param str msg: message to add to WorkerException when raised
    :raises WorkerException: when timeout is reached
    """

    def alarm_handler(signum, frame):
        raise WorkerException(msg)

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(time)


def cancel_timeout_alarm():
    """
    Cancels an exsting timeout alarm (or does nothing if no alarm was set).
    """
    signal.alarm(0)


def check_if_free_space(directory=settings.PROCESSING_TEMP_DIR,
                        min_disk_space_percentage=settings.WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE):
    """
    Checks if there is free disk space in the volume of the given 'directory'. If percentage of free disk space in this
    volume is lower than 'min_disk_space_percentage', this function raises WorkerException.
    :param str directory: path of the directory whose volume will be checked for free space
    :param float min_disk_space_percentage: free disk space percentage to check against
    :raises WorkerException: if available percentage of free space is below the threshold
    """
    stats = os.statvfs(directory)
    percentage_free = stats.f_bfree * 1.0 / stats.f_blocks
    if percentage_free < min_disk_space_percentage:
        raise WorkerException("Disk is running out of space, "
                              "aborting task as there might not be enough space for temp files")


class FreesoundAudioProcessorBase(object):
    """
    Base class to be used for Freesound processing and analysis code.
    It implements methods common to both use cases.
    """

    work_log = ''
    sound = None

    def __init__(self, sound_id):
        self.sound = self.get_sound_object(sound_id)

    def log_info(self, message):
        console_logger.info("%i - %s" % (self.sound.id, message))
        self.work_log += message + '\n'

    def log_error(self, message):
        console_logger.error("%i %s" % (self.sound.id, message))
        self.work_log += message + '\n'

    def set_failure(self, message, error=None):
        logging_message = "sound with id %s failed\n" % self.sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s" % str(error)
        self.log_error(logging_message)

    def get_sound_object(self, sound_id):
        # Import Sound model from apps to avoid circular dependency
        Sound = apps.get_model('sounds.Sound')
        try:
            return Sound.objects.get(id=sound_id)
        except Sound.DoesNotExist:
            raise AudioProcessingException("did not find Sound object with id %s" % sound_id)
        except Exception as e:
            raise AudioProcessingException("unexpected error getting Sound %s from DB" % sound_id)

    def get_sound_path(self):
        sound_path = self.sound.locations('path')
        if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
            sound_path = self.sound.locations('preview.LQ.mp3.path')
        if not os.path.exists(sound_path):
            raise AudioProcessingException('could not find file with path %s' % sound_path)
        self.log_info("file found in " + sound_path)
        return sound_path

    def convert_to_pcm(self, sound_path, tmp_directory, force_use_ffmpeg=False, mono=False):
        """
        Convert a given sound file to PCM. By default we first try to use corresponding decoders for each format and
        preserve original file properties (sampling rate, etc). If conversion fails with this method we failback to
        ffmpeg conversion and set standartized 44.1kHz, 16bit output. ffmpeg conversion still preserves number of
        channels but can be optionally set to output a mono file (useful for analysis code)
        :param sound_path: path of the audiofile to convert
        :param force_use_ffmpeg: don't try to use format specific decoder and go straight to ffmpeg
        :param mono: output mono file (only applies when using ffmpeg conversion)
        :return: path of the converted audio file
        """
        # Convert to PCM and save PCM version in `tmp_wavefile`
        try:
            prefix = "%i_" % self.sound.id if self.sound else "_"
            fh, tmp_wavefile = tempfile.mkstemp(suffix=".wav", prefix=prefix, dir=tmp_directory)
            # Close file handler as we don't use it from Python
            os.close(fh)
            if force_use_ffmpeg:
                raise AudioProcessingException()  # Go to directly to ffmpeg conversion
            if not audioprocessing.convert_to_pcm(sound_path, tmp_wavefile):
                tmp_wavefile = sound_path
                self.log_info("no need to convert, this file is already PCM data")

        except IOError as e:
            # Could not create tmp file
            raise AudioProcessingException("could not create tmp_wavefile file: %s" % e)
        except OSError as e:
            raise AudioProcessingException("conversion to PCM failed, "
                                           "make sure that format conversion executables exist: %s" % e)
        except AudioProcessingException as e:
            # Conversion with format codecs has failed (or skipped using 'force_use_ffmpeg' argument)
            self.log_info("conversion to PCM failed or skipped, now trying conversion with ffmpeg")
            try:
                audioprocessing.convert_using_ffmpeg(sound_path, tmp_wavefile, mono_out=mono)
            except AudioProcessingException as e:
                raise AudioProcessingException("conversion to PCM failed: %s" % e)
            except OSError as e:
                raise AudioProcessingException("conversion to PCM failed, "
                                               "make sure that ffmpeg executable exists: %s" % e)
        except Exception as e:
            raise AudioProcessingException("unhandled exception while converting to PCM: %s" % e)

        self.log_info("PCM file path: " + tmp_wavefile)
        return tmp_wavefile


class FreesoundAudioProcessor(FreesoundAudioProcessorBase):

    def set_failure(self, message, error=None):
        super(FreesoundAudioProcessor, self).set_failure(message, error)
        self.sound.set_processing_ongoing_state("FI")
        self.sound.change_processing_state("FA", processing_log=self.work_log)

    def process(self, skip_previews=False, skip_displays=False):

        with TemporaryDirectory(
                prefix='processing_%s_' % self.sound.id,
                dir=settings.PROCESSING_TEMP_DIR) as tmp_directory:

            # Change ongoing processing state to "processing" in Sound model
            self.sound.set_processing_ongoing_state("PR")

            # Get the path of the original sound and convert to PCM
            try:
                sound_path = self.get_sound_path()
                tmp_wavefile = self.convert_to_pcm(sound_path, tmp_directory)
            except AudioProcessingException as e:
                self.set_failure(e)
                return False

            # Now get info about the file, stereofy it and save new stereofied PCM version in `tmp_wavefile2`
            try:
                fh, tmp_wavefile2 = tempfile.mkstemp(suffix=".wav", prefix="%i_" % self.sound.id, dir=tmp_directory)
                # Close file handler as we don't use it from Python
                os.close(fh)
                info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
            except IOError as e:
                # Could not create tmp file
                self.set_failure("could not create tmp_wavefile2 file", e)
                return False
            except OSError as e:
                self.set_failure("stereofy has failed, "
                                 "make stereofy sure executable exists at %s: %s" % (settings.SOUNDS_PATH, e))
                return False
            except AudioProcessingException as e:
                if "File contains data in an unknown format" in str(e):
                    # Stereofy failed most probably because PCM file is corrupted. This can happen if "convert_to_pcm"
                    # above is skipped because the file is already PCM but it has wrong format. It can also happen in
                    # other occasions where "convert_to_pcm" generates bad PCM files. In this case we try to re-create
                    # the PCM file using ffmpeg and try re-running stereofy
                    self.log_info("stereofy failed, trying re-creating PCM file with ffmpeg and re-running stereofy")
                    try:
                        tmp_wavefile = self.convert_to_pcm(sound_path, tmp_directory, force_use_ffmpeg=True)
                        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH,
                                                                      tmp_wavefile, tmp_wavefile2)
                    except AudioProcessingException as e:
                        self.set_failure("re-run of stereofy with ffmpeg conversion has failed", str(e))
                        return False
                    except Exception as e:
                        self.set_failure("unhandled exception while re-running stereofy with ffmpeg conversion", e)
                        return False
                else:
                    self.set_failure("stereofy has failed", str(e))
                    return False
            except Exception as e:
                self.set_failure("unhandled exception while getting info and running stereofy", e)
                return False

            self.log_info("got sound info and stereofied: " + tmp_wavefile2)

            # Fill audio information fields in Sound object
            try:
                if self.sound.type in settings.LOSSY_FILE_EXTENSIONS:
                    info['bitdepth'] = 0  # mp3 and ogg don't have bitdepth
                    if info['duration'] > 0:
                        raw_bitrate = int(round(old_div(old_div(self.sound.filesize * 8, info['duration']), 1000)))
                        # Here we post-process a bit the bitrate to account for small rounding errors
                        # If we see computed bitrate is very close to a common bitrate, we quantize to that number
                        differences_with_common_bitrates = [abs(cbt - raw_bitrate) for cbt in settings.COMMON_BITRATES]
                        min_difference = min(differences_with_common_bitrates)
                        if min_difference <= 2:
                            info['bitrate'] = settings.COMMON_BITRATES[differences_with_common_bitrates.index(min_difference)]
                        else:
                            info['bitrate'] = raw_bitrate
                    else:
                        info['bitrate'] = 0
                else:
                    info['bitrate'] = 0
                self.sound.set_audio_info_fields(**info)
            except Exception as e:  # Could not catch a more specific exception
                self.set_failure("failed writting audio info fields to db", e)
                return False

            # Generate MP3 and OGG previews
            if not skip_previews:

                # Create directory to store previews (if it does not exist)
                # Same directory is used for all MP3 and OGG previews of a given sound so we only need to run this once
                try:
                    create_directories(os.path.dirname(self.sound.locations("preview.LQ.mp3.path")))
                except OSError:
                    self.set_failure("could not create directory for previews")
                    return False

                # Generate MP3 previews
                for mp3_path, quality in [(self.sound.locations("preview.LQ.mp3.path"), 70),
                                          (self.sound.locations("preview.HQ.mp3.path"), 192)]:
                    try:
                        audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path, quality)
                    except OSError as e:
                        self.set_failure("conversion to mp3 (preview) has failed, "
                                         "make sure that lame executable exists: %s" % e)
                        return False

                    except AudioProcessingException as e:
                        self.set_failure("conversion to mp3 (preview) has failed", e)
                        return False
                    except Exception as e:
                        self.set_failure("unhandled exception generating MP3 previews", e)
                        return False
                    self.log_info("created mp3: " + mp3_path)

                # Generate OGG previews
                for ogg_path, quality in [(self.sound.locations("preview.LQ.ogg.path"), 1),
                                          (self.sound.locations("preview.HQ.ogg.path"), 6)]:
                    try:
                        audioprocessing.convert_to_ogg(tmp_wavefile2, ogg_path, quality)
                    except OSError as e:
                        self.set_failure("conversion to ogg (preview) has failed, "
                                         "make sure that oggenc executable exists: %s" % e)
                        return False
                    except AudioProcessingException as e:
                        self.set_failure("conversion to ogg (preview) has failed", e)
                        return False
                    except Exception as e:
                        self.set_failure("unhandled exception generating OGG previews", e)
                        return False
                    self.log_info("created ogg: " + ogg_path)

            # Generate display images for different sizes and colour scheme front-ends
            if not skip_displays:

                # Create directory to store display images (if it does not exist)
                # Same directory is used for all displays of a given sound so we only need to run this once
                try:
                    create_directories(os.path.dirname(self.sound.locations("display.wave.M.path")))
                except OSError:
                    self.set_failure("could not create directory for displays")
                    return False

                # Generate display images, M and L sizes for NG and BW front-ends
                for width, height, color_scheme, waveform_path, spectral_path in [
                    (120, 71, color_schemes.FREESOUND2_COLOR_SCHEME,
                     self.sound.locations("display.wave.M.path"), self.sound.locations("display.spectral.M.path")),
                    (900, 201, color_schemes.FREESOUND2_COLOR_SCHEME,
                     self.sound.locations("display.wave.L.path"), self.sound.locations("display.spectral.L.path")),
                    (195, 101, color_schemes.BEASTWHOOSH_COLOR_SCHEME,
                     self.sound.locations("display.wave_bw.M.path"), self.sound.locations("display.spectral_bw.M.path")),
                    (780, 301, color_schemes.BEASTWHOOSH_COLOR_SCHEME,
                     self.sound.locations("display.wave_bw.L.path"), self.sound.locations("display.spectral_bw.L.path")),
                ]:
                    try:
                        fft_size = 2048
                        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path, spectral_path, width, height,
                                                           fft_size, color_scheme=color_scheme)
                        self.log_info("created wave and spectrogram images: %s, %s" % (waveform_path, spectral_path))
                    except AudioProcessingException as e:
                        self.set_failure("creation of display images has failed", e)
                        return False
                    except Exception as e:
                        self.set_failure("unhandled exception while generating displays", e)
                        return False

        # Change processing state and processing ongoing state in Sound model
        self.sound.set_processing_ongoing_state("FI")
        self.sound.change_processing_state("OK", processing_log=self.work_log)

        # Copy previews and display files to mirror locations
        copy_previews_to_mirror_locations(self.sound)
        copy_displays_to_mirror_locations(self.sound)

        return True


class FreesoundAudioProcessorBeforeDescription(FreesoundAudioProcessorBase):

    def __init__(self, audio_file_path):
        self.audio_file_path = audio_file_path.encode("utf-8")
        self.output_folder = get_processing_before_describe_sound_folder(self.audio_file_path)
        self.output_wave_path = os.path.join(self.output_folder, 'wave.png')
        self.output_spectral_path = os.path.join(self.output_folder, 'spectral.png')
        self.output_preview_mp3 = os.path.join(self.output_folder, 'preview.mp3')
        self.output_preview_ogg = os.path.join(self.output_folder, 'preview.ogg')
        self.output_info_file = os.path.join(self.output_folder, 'info.json')
        create_directories(os.path.dirname(self.output_preview_ogg))

    def log_info(self, message):
        console_logger.info("{} - {}".format(self.audio_file_path, message))

    def log_error(self, message):
        console_logger.error("{} - {}".format(self.audio_file_path, message))

    def set_failure(self, message, error=None):
        logging_message = "file with path %s failed\n" % self.audio_file_path
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s" % str(error)
        self.log_error(logging_message)

    def get_sound_object(self, sound_id):
        pass

    def get_sound_path(self):
        pass

    def process(self):
        with TemporaryDirectory(
                prefix='processing_before_description_{}_'.format(os.path.basename(self.output_folder)),
                dir=settings.PROCESSING_TEMP_DIR) as tmp_directory:
            tmp_directory = tmp_directory.encode('utf-8')

            # Get the path of the original sound and convert to PCM
            try:
                tmp_wavefile = self.convert_to_pcm(self.audio_file_path, tmp_directory)
            except AudioProcessingException as e:
                self.set_failure(e)
                return False

            # Now get info about the file, stereofy it and save new stereofied PCM version in `tmp_wavefile2`
            try:
                fh, tmp_wavefile2 = tempfile.mkstemp(suffix=".wav", dir=tmp_directory)
                # Close file handler as we don't use it from Python
                os.close(fh)
                info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
            except IOError as e:
                # Could not create tmp file
                self.set_failure("could not create tmp_wavefile2 file", e)
                return False
            except OSError as e:
                self.set_failure("stereofy has failed, "
                                 "make stereofy sure executable exists at %s: %s" % (settings.SOUNDS_PATH, e))
                return False
            except AudioProcessingException as e:
                if "File contains data in an unknown format" in str(e):
                    # Stereofy failed most probably because PCM file is corrupted. This can happen if "convert_to_pcm"
                    # above is skipped because the file is already PCM but it has wrong format. It can also happen in
                    # other occasions where "convert_to_pcm" generates bad PCM files. In this case we try to re-create
                    # the PCM file using ffmpeg and try re-running stereofy
                    self.log_info("stereofy failed, trying re-creating PCM file with ffmpeg and re-running stereofy")
                    try:
                        tmp_wavefile = self.convert_to_pcm(self.audio_file_path, tmp_directory, force_use_ffmpeg=True)
                        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH,
                                                                      tmp_wavefile, tmp_wavefile2)
                    except AudioProcessingException as e:
                        self.set_failure("re-run of stereofy with ffmpeg conversion has failed", str(e))
                        return False
                    except Exception as e:
                        self.set_failure("unhandled exception while re-running stereofy with ffmpeg conversion", e)
                        return False
                else:
                    self.set_failure("stereofy has failed", str(e))
                    return False
            except Exception as e:
                self.set_failure("unhandled exception while getting info and running stereofy", e)
                return False

            self.log_info("got sound info and stereofied: " + tmp_wavefile2)

            # Generate previews
            try:
                audioprocessing.convert_to_mp3(tmp_wavefile2, self.output_preview_mp3, 70)
            except OSError as e:
                self.set_failure("conversion to mp3 (preview) has failed, "
                                    "make sure that lame executable exists: %s" % e)
                return False

            except AudioProcessingException as e:
                self.set_failure("conversion to mp3 (preview) has failed", e)
                return False
            except Exception as e:
                self.set_failure("unhandled exception generating MP3 previews", e)
                return False
            self.log_info("created mp3: " + self.output_preview_mp3)

            try:
                audioprocessing.convert_to_ogg(tmp_wavefile2, self.output_preview_ogg, 1)
            except OSError as e:
                self.set_failure("conversion to ogg (preview) has failed, "
                                    "make sure that oggenc executable exists: %s" % e)
                return False
            except AudioProcessingException as e:
                self.set_failure("conversion to ogg (preview) has failed", e)
                return False
            except Exception as e:
                self.set_failure("unhandled exception generating OGG previews", e)
                return False
            self.log_info("created ogg: " + self.output_preview_ogg)

            # Generate displays
            try:
                audioprocessing.create_wave_images(tmp_wavefile2, self.output_wave_path, self.output_spectral_path, 780, 301,
                                                fft_size=2048, color_scheme=color_schemes.BEASTWHOOSH_COLOR_SCHEME)
                self.log_info("created wave and spectrogram images: %s, %s" % (self.output_wave_path, self.output_spectral_path))
            except AudioProcessingException as e:
                self.set_failure("creation of display images has failed", e)
                return False
            except Exception as e:
                self.set_failure("unhandled exception while generating displays", e)
                return False

            # Save info data to json file
            json.dump(info, open(self.output_info_file, 'w'))
        return True
