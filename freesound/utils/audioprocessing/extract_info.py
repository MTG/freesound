#!/usr/bin/env python

import sys
from processing import audio_info, AudioProcessingException

try:
    for (k,v) in audio_info(sys.argv[1]).items():
        print k,"->", v
except AudioProcessingException, e:
    print "warning, audio information extraction seems to have failed:", e
