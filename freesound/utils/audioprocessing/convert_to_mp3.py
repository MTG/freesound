#!/usr/bin/env python

import sys
from processing import convert_to_mp3, audio_info, AudioProcessingException

convert_to_mp3(sys.argv[1], sys.argv[2])