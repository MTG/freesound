from datetime import datetime
from django.conf import settings
from utils.audioprocessing.processing import AudioProcessingException
import utils.audioprocessing.processing as audioprocessing
import os, tempfile, gearman, shutil, sys


def process(sound):

    def write_log(message):
        sys.stdout.write(str(message)+'\n')
        sys.stdout.flush()

    def failure(message, error=None):
        sound.set_processing_state("FA")
        logging_message = "Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s\n" + str(error)
        write_log(message)

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
    sound.set_processing_state("PR")

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

    # convert to pcm
    to_cleanup = []
    tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))

    try:
        if not audioprocessing.convert_to_pcm(sound.original_path, tmp_wavefile):
            tmp_wavefile = sound.original_path
            success("no need to convert, this file is already pcm data")
        else:
            to_cleanup.append(tmp_wavefile)
            success("converted to pcm: " + tmp_wavefile)
    except AudioProcessingException, e:
        failure("conversion to pcm has failed, trying ffmpeg", e)
        try:
            audioprocessing.convert_using_ffmpeg(sound.original_path, tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
            success("converted to pcm: " + tmp_wavefile)
        except AudioProcessingException, e:
            failure("conversion to pcm with ffmpeg failed", e)
            return False
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False

    tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))

    try:
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        to_cleanup.append(tmp_wavefile2)
    except AudioProcessingException, e:
        failure("stereofy has failed, trying ffmpeg first", e)
        try:
            audioprocessing.convert_using_ffmpeg(sound.original_path, tmp_wavefile)
            info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
            if tmp_wavefile not in to_cleanup: to_cleanup.append(tmp_wavefile)
            to_cleanup.append(tmp_wavefile2)
        except AudioProcessingException, e:
            failure("ffmpeg + stereofy failed", e)
            cleanup(to_cleanup)
            return False
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False

    success("got sound info and stereofied: " + tmp_wavefile2)
    sound.set_audio_info_fields(info)

    for mp3_path, quality in [(sound.locations("preview.LQ.mp3.path"),70), (sound.locations("preview.HQ.mp3.path"), 192)]:
        # create preview
        try:
            os.makedirs(os.path.dirname(mp3_path))
        except OSError:
            pass

        try:
            audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path, quality)
        except AudioProcessingException, e:
            cleanup(to_cleanup)
            failure("conversion to mp3 (preview) has failed", e)
            return False
        except Exception, e:
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
        except AudioProcessingException, e:
            cleanup(to_cleanup)
            failure("conversion to ogg (preview) has failed", e)
            return False
        except Exception, e:
            failure("unhandled exception", e)
            cleanup(to_cleanup)
            return False
        success("created ogg: " + ogg_path)

    # create waveform images M
    waveform_path_m = sound.locations("display.wave.M.path")
    spectral_path_m = sound.locations("display.spectral.M.path")

    try:
        os.makedirs(os.path.dirname(waveform_path_m))
    except OSError:
        pass

    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_m, spectral_path_m, 120, 71, 2048)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("creation of images (M) has failed", e)
        return False
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    success("created previews, medium")

    # create waveform images L
    waveform_path_l = sound.locations("display.wave.L.path")
    spectral_path_l = sound.locations("display.spectral.L.path")
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_l, spectral_path_l, 900, 201, 2048)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("creation of images (L) has failed", e)
        return False
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    success("created previews, large")

    cleanup(to_cleanup)
    sound.set_processing_state("OK")

    return True
