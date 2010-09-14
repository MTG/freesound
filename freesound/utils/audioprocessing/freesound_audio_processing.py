from datetime import datetime
from django.conf import settings
from utils.text import slugify
import logging
import os.path
import shutil
import tempfile
import utils.audioprocessing.processing as audioprocessing

logger = logging.getLogger("audio")

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
    original_filename = os.path.splitext(os.path.basename(sound.original_filename))[0]
    sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(original_filename))
    sound.save()
    paths = sound.paths()

    if not os.path.exists(sound.original_path):
        failure("the file to be processed (%s) isn't there" % sound.original_path)
        return False
    success("found the file %s" % sound.original_path)
    
    # get basic info
    try:
        audio_info = audioprocessing.audio_info(sound.original_path)
    except Exception, e:
        failure("audio information extraction has failed", e)
        return False
    success("got the audio info")
    
    sound.samplerate = audio_info["samplerate"]
    sound.bitrate = audio_info["bitrate"]
    sound.bitdepth = audio_info["bits"]
    sound.channels = audio_info["channels"]
    sound.duration = audio_info["duration"]
    sound.type = audio_info["type"]
    sound.save()
    
    to_cleanup = []
    
    # convert to wave file
    
    tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))

    if sound.type in ["wav", "aiff"]:
        try:
            audioprocessing.convert_to_wav_with_sndfileconvert(sound.original_path, tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
            success("converted to wave file with snd-file: " + tmp_wavefile)
        except Exception, e:
            #failure("conversion to wave file (sndfile) has failed", e)
            #return False
            #success("FAILED to convert file with sndfile, still trying to generate images anyway...")
            #tmp_wavefile = sound.original_path
            try:
                audioprocessing.convert_to_wav(sound.original_path, tmp_wavefile)
            except Exception, e:
                failure("conversion to wave file (mplayer) has failed", e)
                return False
            success("converted to wave file: " + tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
    elif sound.type == "flac":
        try:
            audioprocessing.convert_to_wav_with_flac(sound.original_path, tmp_wavefile)
            to_cleanup.append(tmp_wavefile)
        except Exception, e:
            failure("conversion to wave file (flac) has failed", e)
            return False
        success("converted to wave file with flac: " + tmp_wavefile)
    else: # ogg and mp3, basically...
        try:
            audioprocessing.convert_to_wav(sound.original_path, tmp_wavefile)
        except Exception, e:
            failure("conversion to wave file (mplayer) has failed", e)
            return False
        success("converted to wave file: " + tmp_wavefile)
        to_cleanup.append(tmp_wavefile)
    
    # create preview
    mp3_path = os.path.join(settings.DATA_PATH, paths["preview_path"])
    try:
        os.makedirs(os.path.dirname(mp3_path))
    except OSError:
        pass
    
    try:
        audioprocessing.convert_to_mp3(tmp_wavefile, mp3_path)
    except Exception, e:
        cleanup(to_cleanup)
        failure("conversion to mp3 (preview) has failed", e)
        return False
    success("created mp3: " + mp3_path)
    
    # create waveform images M
    waveform_path_m = os.path.join(settings.DATA_PATH, paths["waveform_path_m"])
    spectral_path_m = os.path.join(settings.DATA_PATH, paths["spectral_path_m"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile, waveform_path_m, spectral_path_m, 120, 71, 2048)
    except Exception, e:
        cleanup(to_cleanup)
        failure("creation of images (M) has failed", e)
        return False
    success("created png, medium size: " + waveform_path_m)

    # create waveform images L
    waveform_path_l = os.path.join(settings.DATA_PATH, paths["waveform_path_l"])
    spectral_path_l = os.path.join(settings.DATA_PATH, paths["spectral_path_l"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile, waveform_path_l, spectral_path_l, 900, 201, 2048)
    except Exception, e:
        cleanup(to_cleanup)
        failure("creation of images (L) has failed", e)
        return False
    success("created png, large size: " + waveform_path_l)

    # now move the original
    new_original_path = os.path.join(settings.DATA_PATH, paths["sound_path"])
    if sound.original_path != new_original_path:
        try:
            os.makedirs(os.path.dirname(new_original_path))
        except OSError:
            pass

        try:
            #shutil.move(sound.original_path, new_original_path)
            shutil.copy(sound.original_path, new_original_path)
        except IOError, e:
            failure("failed to move file from %s to %s" % (sound.original_path, new_original_path), e) 
        success("moved original file from %s to %s" % (sound.original_path, new_original_path))

        sound.original_path = new_original_path
        sound.save()
        
    cleanup(to_cleanup)
    sound.processing_state = "OK"
    sound.save()
    
    return True