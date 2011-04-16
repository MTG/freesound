from datetime import datetime
from django.conf import settings
from utils.audioprocessing.processing import AudioProcessingException
import logging
import os
import shutil
import tempfile
import utils.audioprocessing.processing as audioprocessing

logger = logging.getLogger("audio")

def process_pending():
    from sounds.models import Sound
    for sound in Sound.objects.filter(processing_state="PE").exclude(original_path=None):
        process(sound)
        
def process(sound, do_cleanup=True):
    logger.info("processing audio file %d" % sound.id)
    
    def failure(message, error=None):
        logging_message = "Failed to process audio file: %d\n" % sound.id + message
        sound.processing_log += "failed:" + message + "\n"
        
        if error:
            logging_message += "\n" + str(error)
            sound.processing_log += str(error) + "\n"
        
        logger.error(logging_message)

        sound.processing_state = "FA"
        sound.save()
        
    def success(message):
        sound.processing_log += message + "\n"
        logger.info(message)
    
    def cleanup(files):
        if do_cleanup:
            success("cleaning up files after processing: " + ", ".join(files))
            for filename in files:
                try:
                    os.unlink(filename)
                except:
                    pass
        else:
            success("leaving temporary files..." + ", ".join(files))
    
    # only keep the last processing attempt
    sound.processing_log = "" 
    sound.processing_date = datetime.now()
    sound.save()
    paths = sound.paths()

    if not os.path.exists(sound.original_path):
        failure("the file to be processed (%s) isn't there" % sound.original_path)
        return False
    success("found the file %s" % sound.original_path)
    
    sound.save()

    
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
        failure("conversion to pcm has failed", e)
        return False
    except:
        cleanup(to_cleanup)
        raise
    
    tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
    
    try:
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        to_cleanup.append(tmp_wavefile2)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("stereofy has failed", e)
        return False
    except:
        cleanup(to_cleanup)
        raise
    
    success("got sound info and stereofied: " + tmp_wavefile2)

    sound.samplerate = info["samplerate"]
    sound.bitrate = info["bitrate"]
    sound.bitdepth = info["bitdepth"]
    sound.channels = info["channels"]
    sound.duration = info["duration"]
    sound.save()
    
    # create preview
    mp3_path = os.path.join(settings.SOUNDS_PATH, paths["preview_path"])
    try:
        os.makedirs(os.path.dirname(mp3_path))
    except OSError:
        pass
    
    try:
        audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("conversion to mp3 (preview) has failed", e)
        return False
    except:
        cleanup(to_cleanup)
        raise
    success("created mp3: " + mp3_path)
    
    # create waveform images M
    waveform_path_m = os.path.join(settings.SOUNDS_PATH, paths["waveform_path_m"])
    spectral_path_m = os.path.join(settings.SOUNDS_PATH, paths["spectral_path_m"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_m, spectral_path_m, 120, 71, 2048)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("creation of images (M) has failed", e)
        return False
    except:
        cleanup(to_cleanup)
        raise
    success("created png, medium size: " + waveform_path_m)

    # create waveform images L
    waveform_path_l = os.path.join(settings.SOUNDS_PATH, paths["waveform_path_l"])
    spectral_path_l = os.path.join(settings.SOUNDS_PATH, paths["spectral_path_l"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_l, spectral_path_l, 900, 201, 2048)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("creation of images (L) has failed", e)
        return False
    except:
        cleanup(to_cleanup)
        raise
    success("created png, large size: " + waveform_path_l)
        
    cleanup(to_cleanup)
    sound.processing_state = "OK"
    sound.save()
    
    return True