from datetime import datetime
from django.conf import settings
from utils.text import slugify
import logging
import os.path
import shutil
import tempfile
import utils.audioprocessing.processing as audioprocessing
from utils.audioprocessing.processing import AudioProcessingException, NoSpaceLeftException

logger = logging.getLogger("audio")

def process_pending():
    from sounds.models import Sound
    for sound in Sound.objects.filter(processing_state="PE").exclude(original_path=None):
        process(sound, tmp="/mnt/tmp20m")
        try:
            pass
        except NoSpaceLeftException:
            process(sound, tmp="/tmp/")

def process(sound, do_cleanup=True, tmp="/tmp"):
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
    
    sound.type = audioprocessing.get_sound_type(sound.original_path)
    sound.save()

    
    # convert to pcm
    to_cleanup = []
    tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(sound.id), dir=tmp)
    
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
    
    tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id), dir=tmp)
    
    try:
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        to_cleanup.append(tmp_wavefile2)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("stereofy has failed", e)
        return False
    
    success("got sound info and stereofied: " + tmp_wavefile2)

    sound.samplerate = info["samplerate"]
    sound.bitrate = info["bitrate"]
    sound.bitdepth = info["bitdepth"]
    sound.channels = info["channels"]
    sound.duration = info["duration"]
    sound.save()
    
    # create preview
    mp3_path = os.path.join(settings.DATA_PATH, paths["preview_path"])
    try:
        os.makedirs(os.path.dirname(mp3_path))
    except OSError:
        pass
    
    try:
        audioprocessing.convert_to_mp3(tmp_wavefile2, mp3_path)
    except Exception, e:
        cleanup(to_cleanup)
        failure("conversion to mp3 (preview) has failed", e)
        return False
    success("created mp3: " + mp3_path)
    
    # create waveform images M
    waveform_path_m = os.path.join(settings.DATA_PATH, paths["waveform_path_m"])
    spectral_path_m = os.path.join(settings.DATA_PATH, paths["spectral_path_m"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_m, spectral_path_m, 120, 71, 2048)
    except Exception, e:
        cleanup(to_cleanup)
        failure("creation of images (M) has failed", e)
        return False
    success("created png, medium size: " + waveform_path_m)

    # create waveform images L
    waveform_path_l = os.path.join(settings.DATA_PATH, paths["waveform_path_l"])
    spectral_path_l = os.path.join(settings.DATA_PATH, paths["spectral_path_l"])
    try:
        audioprocessing.create_wave_images(tmp_wavefile2, waveform_path_l, spectral_path_l, 900, 201, 2048)
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