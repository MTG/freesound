from datetime import datetime
from django.conf import settings
from utils.text import slugify
import logging
import os.path
import shutil
import tempfile
import utils.audioprocessing.processing as audioprocessing

logger = logging.getLogger("audio")

def process(sound):
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
        success("cleaning up files after processing")
        for filename in files:
            try:
                os.unlink(filename)
            except:
                pass
    
    # only keep the last processing attempt
    sound.processing_log = "" 
    sound.processing_date = datetime.now()
    original_filename = os.path.splitext(os.path.basename(sound.original_filename))[0]
    sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(original_filename))
    sound.save()
    paths = sound.paths()

    if not os.path.exists(sound.original_path):
        failure("the file to be processed (%s) isn't there" % sound.original_path)
        return False
    else:
        success("found the file %s" % sound.original_path)
    
    # get basic info
    try:
        audio_info = audioprocessing.audio_info(sound.original_path)
        success("got the audio info")
    except Exception, e:
        failure("audio information extraction has failed", e)
        return False
    
    sound.samplerate = audio_info["samplerate"]
    sound.bitrate = audio_info["bitrate"]
    sound.bitdepth = audio_info["bits"]
    sound.channels = audio_info["channels"]
    sound.duration = audio_info["duration"]
    sound.type = audio_info["type"]
    sound.save()
    
    # convert to wave file
    tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
    try:
        audioprocessing.convert_to_wav(sound.original_path, tmp_wavefile)
        success("converted to wave file: " + tmp_wavefile)
    except Exception, e:
        failure("conversion to wave file has failed", e)
        return False
    
    # create preview
    try:
        mp3_path = os.path.join(settings.DATA_PATH, paths["preview_path"])
        try:
            os.makedirs(os.path.dirname(mp3_path))
        except OSError:
            pass
        audioprocessing.convert_to_mp3(tmp_wavefile, mp3_path)
        success("created mp3: " + mp3_path)
    except Exception, e:
        cleanup([tmp_wavefile])
        failure("conversion to mp3 (preview) has failed", e)
        return False
    
    try:
        waveform_path_m = os.path.join(settings.DATA_PATH, paths["waveform_path_m"])
        spectral_path_m = os.path.join(settings.DATA_PATH, paths["spectral_path_m"])
        audioprocessing.create_wave_images(tmp_wavefile, waveform_path_m, spectral_path_m, 120, 71, 2048)
        success("created png, medium size: " + waveform_path_m)
    except Exception, e:
        cleanup([tmp_wavefile])
        failure("creation of images (M) has failed", e)
        return False

    try:
        waveform_path_l = os.path.join(settings.DATA_PATH, paths["waveform_path_l"])
        spectral_path_l = os.path.join(settings.DATA_PATH, paths["spectral_path_l"])
        audioprocessing.create_wave_images(tmp_wavefile, waveform_path_l, spectral_path_l, 900, 201, 2048)
        success("created png, large size: " + waveform_path_l)
    except Exception, e:
        cleanup([tmp_wavefile])
        failure("creation of images (L) has failed", e)
        return False

    # now move the original
    new_original_path = os.path.join(settings.DATA_PATH, paths["sound_path"])
    if sound.original_path != new_original_path:
        try:
            try:
                os.makedirs(os.path.dirname(new_original_path))
            except OSError:
                pass
            #shutil.move(sound.original_path, new_original_path)
            shutil.copy(sound.original_path, new_original_path)
            sound.original_path = new_original_path
            sound.save()
            success("moved original file from %s to %s" % (sound.original_path, new_original_path))
        except IOError, e:
            failure("failed to move file from %s to %s" % (sound.original_path, new_original_path), e) 
        
    cleanup([tmp_wavefile])
    sound.processing_state = "OK"
    sound.save()
    
    return True