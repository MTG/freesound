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
INDEX_DIR = '/freesound-data/similarity_index/'
INDEX_NAME = 'gaia_index_freesound_dev'  # Don't include .db extension in the name here
INDEXING_SERVER_INDEX_NAME = 'background_index'
PRESET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets/')
PRESETS = ['lowlevel', 'pca']
DEFAULT_PRESET = "pca"
SIMILARITY_MINIMUM_POINTS = 2000
LOGFILE = '/var/log/freesound/similarity.log'
LOGFILE_INDEXING_SERVER = '/var/log/freesound/similarity_indexing.log'
LISTEN_PORT = 8008
INDEXING_SERVER_LISTEN_PORT = 8009
PCA_DIMENSIONS = 100
PCA_DESCRIPTORS = [
   "*lowlevel*mean",
   "*lowlevel*dmean",
   "*lowlevel*dmean2",
   "*lowlevel*var",
   "*lowlevel*dvar",
   "*lowlevel*dvar2"
]

# OTHER
SIMILAR_SOUNDS_TO_CACHE = 100
SIMILARITY_CACHE_TIME = 60*60*1
DEFAULT_NUMBER_OF_RESULTS = 15

BAD_REQUEST_CODE = 400
SERVER_ERROR_CODE = 500
NOT_FOUND_CODE = 404

# Graylog GELF endpoint
LOGSERVER_HOST = 'IP_ADDRESS'
LOGSERVER_PORT = 0000

# Set to true to log to stdout in addition to files and graylog
LOG_TO_STDOUT = True
LOG_TO_GRAYLOG = False
LOG_TO_FILE = False
