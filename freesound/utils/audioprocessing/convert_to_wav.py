#!/usr/bin/env python

import sys
from processing import convert_to_wav, audio_info, AudioProcessingException

convert_to_wav(sys.argv[1], sys.argv[2])

try:
    info = audio_info(sys.argv[2])
    if not ( info["bits"] == 16 and info["samplerate"] == 44100 and info["channels"] == 2 and info["duration"] > 0 ):
        print "warning, created file is not 44.1, stereo, 16bit!"
except AudioProcessingException, e:
    print "warning, audio processing seems to have failed:", e