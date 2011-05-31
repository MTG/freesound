import os, logging

INDEX_DIR                   = '/home/fsweb/freesound-similarity/'
PRESET_DIR                  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS                     = ['lowlevel', 'music', 'rhythm', 'timbre']
SIMILARITY_MINIMUM_POINTS   = 10000
REQREP_ADDRESS              = "tcp://10.55.0.104:9070" #cuernavaca.s.upf.edu
NUM_THREADS                 = 5
LOGFILE                     = '/var/log/freesound/similarity.log'
LOGFILE_LEVEL               = logging.DEBUG
