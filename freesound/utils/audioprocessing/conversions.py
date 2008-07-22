import os
import subprocess
import re

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


def detect_type(input_filename):
    command = ["mplayer", "-vo", "null", "-identify", "-frames", "0", input_filename]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = process.communicate()
    
    if process.returncode != 0:
        raise AudioProcessingException, stdout

    samplerate = -1
    bitrate = -1
    bits = -1
    channels = -1
    type = ""

    lines = stdout.split("\n")
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("AUDIO:"):
            try:
                p = re.compile( '[^\d,]')
                bits = int(p.sub( '', line).split(',')[2])
            except:
                pass
        if line.startswith("ID_AUDIO_BITRATE"):
            bitrate = int(line.split("=")[1])
        elif line.startswith("ID_AUDIO_RATE"):
            samplerate = int(line.split("=")[1])
        elif line.startswith("ID_AUDIO_NCH"):
            channels = int(line.split("=")[1])
        elif line.startswith("ID_AUDIO_CODEC"):
            types = {'ffvorbis': "ogg", "ffflac": "flac", "pcm": "wav", "mp3": "mp3"}
            type = types[line.split("=")[1]]

    if input_filename.endswith("aiff") or input_filename.endswith("aif") and type == "wav":
        type = "aiff"

    if bits == -1:
        bits = bitrate/(samplerate*channels)
    
    return {"type": type, "channels": channels, "bits": bits, "samplerate": samplerate, "bitrate": bitrate}
    

def convert_to_mp3(input_filename, output_filename, quality):
    # converts 
    pass


if __name__ == "__main__":
    import sys
    try:
        for c in sys.argv[1:]:
            print "------", os.path.basename(c), "-------------------------------------"
            print detect_type(c)
    except AudioProcessingException, e:
        print "ERROR ERROR\n", e
        
