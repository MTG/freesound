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
from utils.audioprocessing.processing import AudioProcessingException
import color_schemes
import utils.audioprocessing.processing as audioprocessing
from utils.mirror_files import copy_previews_to_mirror_locations, copy_displays_to_mirror_locations
import os, tempfile, shutil, sys
import logging

logger = logging.getLogger("processing")


def process(sound):

    def write_log(message):
        logger.info("[%d] %i: %s" % (os.getpid(),sound.id,message))
        sys.stdout.write(str(message)+'\n')
        sys.stdout.flush()

    def failure(message, error=None):
        sound.set_processing_ongoing_state("FI")
        sound.change_processing_state("FA", use_set_instead_of_save=True)
        logging_message = "Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s\n" % str(error)
        write_log(logging_message)

    def success(message):
        write_log(message)

    def cleanup(files):
        success("cleaning up files after processing: " + ", ".join(files))
        for filename in files:
            try:
                os.unlink(filename)
            except:
                pass

    # not saving the date of the processing attempt anymore
    sound.set_processing_ongoing_state("PR")

    new_path = sound.locations('path')
    # Is the file at its new location?
    if not os.path.exists(new_path):
        # Is the file at its old location?
        if not sound.original_path or not os.path.exists(sound.original_path):
            failure("The file to be processed can't be found at its FS1 nor at its FS2 location.")
            return False
        else:
            success("Found the file at its FS1 location: %s" % sound.original_path)
            if not sound.original_path.startswith('/mnt/freesound-data/'):
                failure("The file appears to be in a weird location and not in '/mnt/freesound-data/'!.")
                return False
            success("Copying file from %s to %s" % (sound.original_path, new_path))
            dest_dir = os.path.dirname(new_path)
            if not os.path.exists(dest_dir):
                try:
                    os.makedirs(dest_dir)
                except:
                    failure("Could not create destination directory %s" % dest_dir)
                    return False
            shutil.copy(sound.original_path, new_path)
            sound.set_original_path(new_path)
            success("Copied file from its FS1 to FS2 location.")
    else:
        success("Found the file at its FS2 location: %s" % new_path)
        if sound.original_path != new_path:
            sound.set_original_path(new_path)
            sound.refresh_from_db()

    # convert to pcm
    to_cleanup = []
    try:
        tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
    except IOError as e:
        # Could not create tmp file
        failure("could not create tmp file", e)

    try:
        if not audioprocessing.convert_to_pcm(sound.original_path, tmp_wavefile):
            tmp_wavefile = sound.original_path
            success("no need to convert, this file is already pcm data")
        else:
            to_cleanup.append(tmp_wavefile)
            success("converted to pcm: " + tmp_wavefile)
    except AudioProcessingException as e:
        failure("conversion to pcm has failed, trying ffmpeg", e)
        try:
            audioprocessing.convert_using_ffmpeg(sound.original_path, tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
            success("converted to pcm: " + tmp_wavefile)
        except AudioProcessingException as e:
            failure("conversion to pcm with ffmpeg failed", e)
            return False
    except Exception as e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False

    tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))

    try:
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        to_cleanup.append(tmp_wavefile2)
    except AudioProcessingException as e:
        failure("stereofy has failed, trying ffmpeg first", e)
        try:
            audioprocessing.convert_using_ffmpeg(sound.original_path, tmp_wavefile)
            info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
            #if tmp_wavefile not in to_cleanup: to_cleanup.append(tmp_wavefile)
            to_cleanup.append(tmp_wavefile2)
        except AudioProcessingException as e:
            failure("ffmpeg + stereofy failed", e)
            cleanup(to_cleanup)
            return False
    except Exception as e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False

    success("got sound info and stereofied: " + tmp_wavefile2)
    if sound.type in ["mp3","ogg","m4a"]:
        info['bitdepth']=0 # mp3 and ogg don't have bitdepth

    try:
        sound.set_audio_info_fields(info)
    except Exception as e:  # Could not catch a more specific exception
        failure("failed writting audio info fields to db", e)

    for mp3_path, quality in [(sound.locations("preview.LQ.mp3.path"),70), (sound.locations("preview.HQ.mp3.path"), 192)]:
        # create preview
        try:
            os.makedirs(os.path.dirname(mp3_path))
        except OSError:
            pass

        try:
            audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path, quality)
        except AudioProcessingException as e:
            cleanup(to_cleanup)
            failure("conversion to mp3 (preview) has failed", e)
            return False
        except Exception as e:
            failure("unhandled exception", e)
            cleanup(to_cleanup)
            return False
        success("created mp3: " + mp3_path)

    for ogg_path, quality in [(sound.locations("preview.LQ.ogg.path"),1), (sound.locations("preview.HQ.ogg.path"), 6)]:
        # create preview
        try:
            os.makedirs(os.path.dirname(ogg_path))
        except OSError:
            pass

        try:
            audioprocessing.convert_to_ogg(tmp_wavefile2, ogg_path, quality)
        except AudioProcessingException as e:
            cleanup(to_cleanup)
            failure("conversion to ogg (preview) has failed", e)
            return False
        except Exception as e:
            failure("unhandled exception", e)
            cleanup(to_cleanup)
            return False
        success("created ogg: " + ogg_path)

    # create waveform images M
    waveform_path_m = sound.locations("display.wave.M.path")
    spectral_path_m = sound.locations("display.spectral.M.path")
    waveform_bw_path_m = sound.locations("display.wave_bw.M.path")
    spectral_bw_path_m = sound.locations("display.spectral_bw.M.path")

    try:
        os.makedirs(os.path.dirname(waveform_path_m))
    except OSError:
        pass

    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_m, spectral_path_m, 120, 71, 2048,
                                           color_scheme=color_schemes.FREESOUND2_COLOR_SCHEME)
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_bw_path_m, spectral_bw_path_m, 500, 201, 2048,
                                           color_scheme=color_schemes.BEASTWHOOSH_COLOR_SCHEME)
    except AudioProcessingException as e:
        cleanup(to_cleanup)
        failure("creation of images (M) has failed", e)
        return False
    except Exception as e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    success("created image (medium)")

    # create waveform images L
    waveform_path_l = sound.locations("display.wave.L.path")
    spectral_path_l = sound.locations("display.spectral.L.path")
    waveform_bw_path_l = sound.locations("display.wave_bw.L.path")
    spectral_bw_path_l = sound.locations("display.spectral_bw.L.path")
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_l, spectral_path_l, 900, 201, 2048,
                                           color_scheme=color_schemes.FREESOUND2_COLOR_SCHEME)
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_bw_path_l, spectral_bw_path_l, 1500, 401, 2048,
                                           color_scheme=color_schemes.BEASTWHOOSH_COLOR_SCHEME)
    except AudioProcessingException as e:
        cleanup(to_cleanup)
        failure("creation of images (L) has failed", e)
        return False
    except Exception as e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    success("created images (large)")

    cleanup(to_cleanup)
    sound.set_processing_ongoing_state("FI")
    sound.change_processing_state("OK", use_set_instead_of_save=True)

    # Copy previews and display files to mirror locations
    copy_previews_to_mirror_locations(sound)
    copy_displays_to_mirror_locations(sound)

    return True
