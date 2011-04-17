from datetime import datetime
from django.conf import settings
from utils.audioprocessing.processing import AudioProcessingException
import os
import tempfile
import utils.audioprocessing.processing as audioprocessing

def process_sound_via_gearman(sound, gm_client=None):
    if not gm_client:
        import gearman
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
    sound.processing_date = datetime.now()
    sound.processing_state = "PR" # processing
    sound.save()
    gm_client.submit_job("process_sound", str(sound.id), wait_until_complete=False, background=True)
        
def process(sound):
    def failure(message, error=None):
        logging_message = "Failed to process audio file: %d\n" % sound.id + message
        sound.processing_log += "failed:" + message + "\n"
        
        if error:
            logging_message += "\n" + str(error)
            sound.processing_log += str(error) + "\n"

        sound.processing_state = "FA"
        sound.save()
        
    def success(message):
        sound.processing_log += message + "\n"
    
    def cleanup(files):
        success("cleaning up files after processing: " + ", ".join(files))
        for filename in files:
            try:
                os.unlink(filename)
            except:
                pass
    
    # only keep the last processing attempt
    sound.processing_log = "" 
    sound.processing_date = datetime.now()
    sound.save()

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
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    
    tmp_wavefile2 = tempfile.mktemp(suffix=".wav", prefix=str(sound.id))
    
    try:
        info = audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, tmp_wavefile, tmp_wavefile2)
        to_cleanup.append(tmp_wavefile2)
    except AudioProcessingException, e:
        cleanup(to_cleanup)
        failure("stereofy has failed", e)
        return False
    except Exception, e:
        failure("unhandled exception", e)
        cleanup(to_cleanup)
        return False
    
    success("got sound info and stereofied: " + tmp_wavefile2)

    sound.samplerate = info["samplerate"]
    sound.bitrate = info["bitrate"]
    sound.bitdepth = info["bitdepth"]
    sound.channels = info["channels"]
    sound.duration = info["duration"]
    sound.save()
    
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
    sound.processing_state = "OK"
    sound.processing_date = datetime.now()
    sound.save()
    
    return True