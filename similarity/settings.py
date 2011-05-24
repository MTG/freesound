import os

INDEX_DIR                   = '/home/fsweb/freesound-similarity/'
PRESET_DIR                  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS                     = ['lowlevel', 'music', 'rhythm', 'timbre']
SIMILARITY_MINIMUM_POINTS   = 10000
REQREP_ADDRESS              = "tcp://cuernavaca.s.upf.edu:9070"
NUM_THREADS                 = 5
