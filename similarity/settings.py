import os, logging

INDEX_DIR                   = '/home/fsweb/freesound-similarity/'
PRESET_DIR                  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS                     = ['lowlevel', 'music'] #, 'sfx', 'lowlevelplus']
SIMILARITY_MINIMUM_POINTS   = 2000
REQREP_ADDRESS              = "tcp://10.55.0.104:9070" #cuernavaca.s.upf.edu
NUM_THREADS                 = 5
LOGFILE                     = '/var/log/freesound/similarity.log'
READ_TIMEOUT                = 10
UPDATE_TIMEOUT              = 20
