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
LOGFILE                     = '/var/log/freesound/tagrecommendation.log'
LISTEN_PORT                 = 8010
RECOMMENDATION_DATA_DIR     = '/Users/frederic/SMC/Freesound/freesound-tagrecommendation/'

# CLIENT SETTINGS (to be moved to django settings?)
TAGRECOMMENDATION_ADDRESS          = 'localhost'
TAGRECOMMENDATION_PORT             = 8010
TAGRECOMMENDATION_CACHE_TIME       = 60*60*24*7 # One week?

# OTHER
USE_COMMUNITY_BASED_RECOMMENDERS = True
CLASSES = {
    'FX':'Collection CFX.json',
    'Soundscape':'Collection CSoundscape.json',
    'Music':'Collection CMusic.json',
    'Samples':'Collection CSamples.json',
    'Speech':'Collection CSpeech.json',
}

USE_KEYTAGS = True
KEY_TAGS = {
    'FX': ['fx', 'effect', 'foley'],
    'Soundscape': ['field-recording', 'soundscape', 'ambient'],
    'Music': ['music', 'loop'],
    'Samples': ['multisample', 'sample', 'instrument'],
    'Speech': ['speech', 'voice'],
}

