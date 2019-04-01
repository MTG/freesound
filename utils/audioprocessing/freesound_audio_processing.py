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
import sys
import tempfile

from django.conf import settings

import color_schemes
import utils.audioprocessing.processing as audioprocessing
from utils.audioprocessing.processing import AudioProcessingException
from utils.mirror_files import copy_previews_to_mirror_locations, copy_displays_to_mirror_locations

logger = logging.getLogger("processing")


def process(sound, skip_previews=False, skip_displays=False):

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

    def failure(message, error=None):
        sound.set_processing_ongoing_state("FI")
        sound.change_processing_state("FA", use_set_instead_of_save=True)
        logging_message = "ERROR: Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s" % str(error)
        write_log(logging_message)
        cleanup(to_cleanup)

    def success(message):
        write_log('- ' + message)

    to_cleanup = []  # This will hold a list of files to cleanup after processing

    # Change ongoing processing state to "processing" in Sound model
    sound.set_processing_ongoing_state("PR")

    # Get the path of the original sound
    sound_path = sound.locations('path')
    if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
        sound_path = sound.locations('preview.LQ.mp3.path')
    if not os.path.exists(sound_path):
        failure("can't process sound as file does not exist")
        return False
    success("file to process found in " + sound_path)

    # Convert to PCM and save PCM version in `tmp_wavefile`
    try:
        tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
        if not audioprocessing.convert_to_pcm(sound_path, tmp_wavefile):
            tmp_wavefile = sound_path
            success("no need to convert, this file is already PCM data")
        else:
            to_cleanup.append(tmp_wavefile)
            success("converted to pcm: " + tmp_wavefile)
    except IOError as e:
        # Could not create tmp file
        failure("could not create tmp_wavefile file", e)
        return False
    except AudioProcessingException as e:
        try:
            audioprocessing.convert_using_ffmpeg(sound_path, tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
            success("converted to PCM: " + tmp_wavefile)
        except AudioProcessingException as e:
            failure("conversion to PCM failed", e)
            return False
    except Exception as e:
        failure("unhandled exception while converting to PCM", e)
        return False

    # Now get info about the file, stereofy it and save new stereofied PCM version in `tmp_wavefile2`
    try:
        tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
        to_cleanup.append(tmp_wavefile2)
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        if sound.type in ["mp3", "ogg", "m4a"]:
            info['bitdepth'] = 0  # mp3 and ogg don't have bitdepth
        success("got sound info and stereofied: " + tmp_wavefile2)
    except IOError as e:
        # Could not create tmp file
        failure("could not create tmp_wavefile2 file", e)
        return False
    except AudioProcessingException as e:
        failure("stereofy has failed", e)
        return False
    except Exception as e:
        failure("unhandled exception while getting info and running stereofy", e)
        return False

    # Fill audio information fields in Sound object
    try:
        sound.set_audio_info_fields(info)
    except Exception as e:  # Could not catch a more specific exception
        failure("failed writting audio info fields to db", e)
        return False

    # Generate MP3 and OGG previews
    if not skip_previews:

        # Create directory to store previews (if it does not exist)
        # Same directory is used for all MP3 and OGG previews of a given sound so we only need to run this once
        try:
            create_directory(os.path.dirname(sound.locations("preview.LQ.mp3.path")))
        except OSError:
            failure("could not create directory for previews")
            return False

        # Generate MP3 previews
        for mp3_path, quality in [(sound.locations("preview.LQ.mp3.path"), 70),
                                  (sound.locations("preview.HQ.mp3.path"), 192)]:
            try:
                audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path, quality)
            except AudioProcessingException as e:
                failure("conversion to mp3 (preview) has failed", e)
                return False
            except Exception as e:
                failure("unhandled exception generating MP3 previews", e)
                return False
            success("created mp3: " + mp3_path)

        # Generate OGG previews
        for ogg_path, quality in [(sound.locations("preview.LQ.ogg.path"), 1),
                                  (sound.locations("preview.HQ.ogg.path"), 6)]:
            try:
                audioprocessing.convert_to_ogg(tmp_wavefile2, ogg_path, quality)
            except AudioProcessingException as e:
                failure("conversion to ogg (preview) has failed", e)
                return False
            except Exception as e:
                failure("unhandled exception generating OGG previews", e)
                return False
            success("created ogg: " + ogg_path)

    # Generate display images for different sizes and colour scheme front-ends
    if not skip_displays:

        # Create directory to store display images (if it does not exist)
        # Same directory is used for all displays of a given sound so we only need to run this once
        try:
            create_directory(os.path.dirname(sound.locations("display.wave.M.path")))
        except OSError:
            failure("could not create directory for displays")
            return False

        # Generate display images, M and L sizes for NG and BW front-ends
        for width, height, color_scheme, waveform_path, spectral_path in [
            (120, 71, color_schemes.FREESOUND2_COLOR_SCHEME,
             sound.locations("display.wave.M.path"), sound.locations("display.spectral.M.path")),
            (500, 201, color_schemes.BEASTWHOOSH_COLOR_SCHEME,
             sound.locations("display.wave_bw.M.path"), sound.locations("display.spectral_bw.M.path")),
            (900, 201, color_schemes.FREESOUND2_COLOR_SCHEME,
             sound.locations("display.wave.L.path"), sound.locations("display.spectral.L.path")),
            (1500, 401, color_schemes.BEASTWHOOSH_COLOR_SCHEME,
             sound.locations("display.wave_bw.L.path"), sound.locations("display.spectral_bw.L.path"))
        ]:
            try:
                fft_size = 2048
                audioprocessing.create_wave_images(tmp_wavefile2, waveform_path, spectral_path, width, height,
                                                   fft_size, color_scheme=color_scheme)
                success("created wave and spectrogram images: %s, %s" % (waveform_path, spectral_path))
            except AudioProcessingException as e:
                failure("creation of display images has failed", e)
                return False
            except Exception as e:
                failure("unhandled exception while generating displays", e)
                return False

    # Clean up temp files
    cleanup(to_cleanup)

    # Change processing state and processing ongoing state in Sound model
    sound.set_processing_ongoing_state("FI")
    sound.change_processing_state("OK", use_set_instead_of_save=True)

    # Copy previews and display files to mirror locations
    copy_previews_to_mirror_locations(sound)
    copy_displays_to_mirror_locations(sound)

    return True
