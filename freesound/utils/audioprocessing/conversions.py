from django.utils import simplejson
import os
import subprocess
import re

class AudioProcessingException(Exception):
    pass


def convert_to_wav(input_filename, output_filename):
    # converts any audio file type to wav, 44.1, 16bit, stereo
    # uses mplayer to play whatever, and store the format as a wave file
    
    if not os.path.exists(input_filename):
        raise AudioProcessingException, "file does not exist"
    
    command = ["mplayer", "-vc", "null", "-vo", "null", "-af", "channels=2,resample=44100:0:0", "-ao", "pcm:fast:file=\"%s\"" % output_filename, input_filename]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = process.communicate()
    
    if process.returncode != 0 or not os.path.exists(output_filename):
        raise AudioProcessingException, stdout
    
    return stdout


def audio_info(input_filename):
    # extract samplerate, channels, ... from an audio file using getid3
    
    if not os.path.exists(input_filename):
        raise AudioProcessingException, "file does not exist"
    
    command = ["./extract_audio_data.php", input_filename]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = process.communicate()
    
    parsed = simplejson.loads(stdout)
    
    if "error" in parsed:
        raise AudioProcessingException, "extract_audio_data error: " + parsed["error"]

    return dict(samplerate=parsed["sample_rate"], bitrate=parsed["avg_bit_rate"], bits=parsed["bits_per_sample"], channels=parsed["channels"], type=parsed["format_name"], duration=parsed["playing_time"])
    

def convert_to_mp3(input_filename, output_filename, quality):
    # converts 
    pass


if __name__ == "__main__":
    import sys

    for c in sys.argv[1:]:
        print "------", os.path.basename(c), "-------------------------------------"
        
        wav_filename = os.path.join("wavs", os.path.splitext(os.path.basename(c))[0]) + '.wav'

        try:
            convert_to_wav(c, wav_filename)
            print "conversion to wav done"
        except AudioProcessingException, e:
            print "error converting", e
            
        try:
            info = audio_info(c)
            for (k,v) in info.iteritems():
                print k, ":", v
        except AudioProcessingException, e:
            print "error extracting info", e