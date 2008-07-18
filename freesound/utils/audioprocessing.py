import os
import subprocess

class AudioProcessingException(Exception):
    pass


def convert_to_wav(input_filename, output_filename):
    # converts any audio file type to wav, 44.1, 16bit, stereo
    
    command = ["mplayer", "-vc", "null", "-vo", "null", "-af", "channels=2,resample=44100:0:0", "-ao", "pcm:fast:file=\"%s\"" % output_filename, input_filename]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = process.communicate()
    
    if process.returncode != 0 or not os.path.exists(output_filename):
        raise AudioProcessingException, stdout
    
    return stdout
    
def convert_to_mp3(input_filename, output_filename, quality):
    # converts 
    pass


if __name__ == "__main__":
    import sys
    try:
        print convert_to_wav(sys.argv[1], sys.argv[1] + ".wav")
    except AudioProcessingException, e:
        print "ERROR ERROR\n", e
        
