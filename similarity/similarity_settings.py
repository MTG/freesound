#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import os
# NOTE: In production and test this file is taken from the deploy repository

# SERVER SETTINGS
INDEX_DIR                   = '/home/frederic/Freesound/freesound-similarity/'#'/home/fsweb/freesound/freesound-similarity/'
INDEX_NAME                  = 'fs_index'
PRESET_DIR                  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS                     = ['lowlevel','spectral_centroid'] # 'music'
DEFAULT_PRESET              = "lowlevel"
SIMILARITY_MINIMUM_POINTS   = 2000
LOGFILE                     = '/var/log/freesound/similarity.log'
LISTEN_PORT                 = 8000

# CLIENT SETTINGS (to be moved to django settings?)
SIMILARITY_ADDRESS          = '127.0.0.1' #'10.55.0.42'
SIMILARITY_PORT             = 8000

# OTHER
SIMILAR_SOUNDS_TO_CACHE = 100
SIMILARITY_CACHE_TIME = 60*60*1
DEFAULT_NUMBER_OF_RESULTS = 15

