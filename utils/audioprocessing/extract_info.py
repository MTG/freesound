#!/usr/bin/env python

import sys
from processing import stereofy_and_find_info, AudioProcessingException

try:
    for (k,v) in stereofy_and_find_info("/Users/bram/Development/nightingale/sandbox/legacy/stereofy/stereofy", sys.argv[1], '/dev/null').items():
        print k,"->", v
except AudioProcessingException, e:
    print "warning, audio information extraction seems to have failed:", e
