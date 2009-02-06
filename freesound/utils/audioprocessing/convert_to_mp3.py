#!/usr/bin/env python

import sys
from processing import convert_to_mp3, audio_info, AudioProcessingException

for filename in sys.argv[1:]:
    convert_to_mp3(filename, filename[:-3] + "mp3")