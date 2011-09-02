from settings import ESSENTIA_EXECUTABLE
import os, shutil, subprocess, signal, sys

def analyze(sound):
    FFMPEG_TIMEOUT = 3 * 60
    tmp_conv = False

    def  alarm_handler(signum, frame):
        raise Exception("timeout while waiting for ffmpeg")

    #TODO: refactor processing and analysis together
    def write_log(message):
        sys.stdout.write(str(message)+'\n')
        sys.stdout.flush()

    def failure(message, error=None):
        sound.set_analysis_state("FA")
        logging_message = "Failed to process sound with id %s\n" % sound.id
        logging_message += "\tmessage: %s\n" % message
        if error:
            logging_message += "\terror: %s\n" + str(error)
        write_log(message)

    try:
        statistics_path = sound.locations("analysis.statistics.path")
        frames_path = sound.locations("analysis.frames.path")
        input_path = sound.locations('path')

        if not os.path.exists(input_path):
            failure('Could not find file with path %s'% input_path)
            return False

        if os.path.getsize(input_path) >50 * 1024 * 1024: #same as filesize_warning in sound model
            failure('File is larger than 50MB. Passing on it.')
            return False

        ext = os.path.splitext(input_path)[1]
        if ext in ['.wav', '.aiff', '.aifc', '.aif']:
            tmp_conv = True
            tmp_wav_path = '/tmp/conversion_%s.wav' % sound.id
            try:
                p = subprocess.Popen(['ffmpeg', '-y', '-i', input_path, '-acodec', 'pcm_s16le',
                                  '-ac', '1', '-ar', '44100', tmp_wav_path])
                signal.signal(signal.SIGALRM, alarm_handler)
                signal.alarm(FFMPEG_TIMEOUT)
                p.wait()
                signal.alarm(0)
            except Exception, e:
                failure("ffmpeg conversion failed ",e)
                return False
            input_path = tmp_wav_path
        tmp_ana_path = '/tmp/analysis_%s' % sound.id
        essentia_dir = os.path.dirname(os.path.abspath(ESSENTIA_EXECUTABLE))
        os.chdir(essentia_dir)
        exec_array = [ESSENTIA_EXECUTABLE, input_path, tmp_ana_path]

        try:
            p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_result = p.wait()
            if p_result != 0:
                output_std, output_err = p.communicate()
                failure( "Essentia extractor returned an error (%s) stdout:%s stderr: %s"%(p_result, output_std, output_err))
                return False
        except Exception, e:
            failure("Essentia extractor failed ",e)
            return False

        __create_dir(statistics_path)
        __create_dir(frames_path)
        shutil.move('%s.yaml' % tmp_ana_path, statistics_path)
        shutil.move('%s_frames.json' % tmp_ana_path, frames_path)
        os.remove('%s.json' % tmp_ana_path)
        sound.set_analysis_state('OK')
    except:
        failure("Unexpected error in analysis ",e)
        return False
    finally:
        if tmp_conv:
            os.remove(tmp_wav_path)
    return True

def __create_dir(path):
    dir_path = os.path.dirname(os.path.abspath(path))
    if not  os.path.exists(dir_path):
        os.makedirs(dir_path)
