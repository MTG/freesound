from settings import ESSENTIA_EXECUTABLE
import os, shutil, subprocess

def analyze(sound):
    statistics_path = sound.locations("analysis.statistics.path")
    frames_path = sound.locations("analysis.frames.path")
    # don't recalculate if the files are already there:

    if os.path.exists(statistics_path) and os.path.exists(frames_path):
        return True

    input_path = sound.original_path
    tmp_conv = False
    ext = os.path.splitext(input_path)[1]
    if ext in ['.wav', '.aiff', '.aifc', '.aif']:
        tmp_conv = True
        tmp_wav_path = '/tmp/conversion_%s.wav' % sound.id
        p = subprocess.Popen(['ffmpeg', '-y', '-i', input_path, '-acodec', 'pcm_s16le',
                              '-ac', '1', '-ar', '44100', tmp_wav_path])
        p.wait()
        input_path = tmp_wav_path
    # the essentia extractor outputs 3 files
    # - /tmp/analysis_34627.json (statistics)
    # - /tmp/analysis_34627.yaml (statistics)
    # - /tmp/analysis_34627_frames.json (frame level descriptors)
    tmp_ana_path = '/tmp/analysis_%s' % sound.id
    essentia_dir = os.path.dirname(os.path.abspath(ESSENTIA_EXECUTABLE))
    os.chdir(essentia_dir)
    exec_array = [ESSENTIA_EXECUTABLE, input_path, tmp_ana_path]
    p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p_result = p.wait()
    if p_result != 0:
        output_std, output_err = p.communicate()
        raise Exception(
"""Processing file with id %s and path %s failed.
    return code:
        %s
    STDOUT:
        %s
    STDERR:
        %s
""" % (sound.id, input_path, p_result, output_std, output_err))
    else:
        __create_dir(statistics_path)
        __create_dir(frames_path)
        shutil.move('%s.yaml' % tmp_ana_path, statistics_path)
        shutil.move('%s_frames.json' % tmp_ana_path, frames_path)
        os.remove('%s.json' % tmp_ana_path)
    if tmp_conv:
        os.remove(tmp_wav_path)
    return True

def __create_dir(path):
    dir_path = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(dir_path)
    except:
        pass
