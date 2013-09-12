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
RECOMMENDATION_DATA_DIR     = '/Users/frederic/SMC/Freesound/freesound-tagrecommendation/' #'/home/frederic/Freesound/freesound-tagrecommendation/' #'/Users/frederic/SMC/Freesound/freesound-tagrecommendation/'

# CLIENT SETTINGS (to be moved to django settings?)
TAGRECOMMENDATION_ADDRESS          = 'localhost'
TAGRECOMMENDATION_PORT             = 8010
TAGRECOMMENDATION_CACHE_TIME       = 60*60*24*7 # One week?

# OTHER
DATABASE = "FREESOUND2012"
CLASSES = {
    'FX': 'CFX',
    'Soundscape': 'CSoundscape',
    'Music': 'CMusic',
    'Samples': 'CSamples',
    'Speech': 'CSpeech',
}


# This tag recommendation server needs some data files to be in the data folder
#
# For the class detection step:
#   Classifier.pkl              (precomputed classifier pickled)
#   Classifier_meta.json        (metadata of the classifier)
#   Classifier_TAG_NAMES.npy    (vector of all tag names used to train the classifier)
#
# For every class used:
#   [[DATABASE]]_[[CLASSNAME]]_SIMILARITY_MATRIX_cosine_SUBSET.npy
#   [[DATABASE]]_[[CLASSNAME]]_SIMILARITY_MATRIX_cosine_SUBSET_TAG_NAMES.npy
# Example:
#   FREESOUND2012_CFX_SIMILARITY_MATRIX_cosine_SUBSET.npy
#   FREESOUND2012_CFX_SIMILARITY_MATRIX_cosine_SUBSET_TAG_NAMES.npy
#   ...
#
# If these files are recalcuated and placed at the correct directory, the recommendation service
# can reload the matrixs using the method "reload" -> tagrecommendation/reload


