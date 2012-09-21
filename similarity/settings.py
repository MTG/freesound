import os

INDEX_DIR                   = '/home/frederic/Desktop/freesound-similarity/'#'/home/fsweb/freesound-similarity/'
PRESET_DIR                  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS                     = ['lowlevel','spectral_centroid'] # 'music'
DEFAULT_PRESET              = "lowlevel"
SIMILARITY_MINIMUM_POINTS   = 2000
LOGFILE                     = '/var/log/freesound/new_similarity.log'



