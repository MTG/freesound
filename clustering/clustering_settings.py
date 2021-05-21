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


# Directory where the Gaia dataset index files are located.
INDEX_DIR = '/freesound-data/clustering_index/'

# Configuration of the features used for clustering or evaluation.
# We define here for each features the Gaia dataset index file, the descriptor name within the dataset 
# and the metric used for similarity computation.
# The minimum requirement is to have one available set of features and set it as the default features
# used for clustering (see variable bellow).
AVAILABLE_FEATURES = {
    # AudioSet Features (feature vector of the frame of max energy)
    'AUDIOSET_FEATURES': {
        'DATASET_FILE': 'FS_AS_embeddings_mean_max_min_nrg_normalized',
        'GAIA_DESCRIPTOR_NAMES': 'AS_embeddings_ppc_max_energy',
        'GAIA_METRIC': 'euclidean'
    },
    # tag-based features used as reference features (Bag of Words - LDA)
    'TAG_DERIVED_FEATURES': None,
}

# Default features used for clustering
DEFAULT_FEATURES = 'AUDIOSET_FEATURES'

# Key of AVAILABLE_FEATURES used for evaluating the clustering results
# Typically tag-derived features
REFERENCE_FEATURES = None

# Maximum number of results to cluster
MAX_RESULTS_FOR_CLUSTERING = 1000

# Cache settings
# One day timeout for keeping clustering results. The cache timer is reset when the clustering is 
# requested so that popular queries that are performed once a day minimum will always stay in cache
# and won't be recomputed.
CLUSTERING_CACHE_TIME = 24*60*60*1
# One minute timeout for keeping the pending state. When a clustering is being performed async in a 
# Celery worker, we consider the clustering as pending for only 1 minute. This may be useful if a 
# worker task got stuck. There should be a settings in celery to stop a worker task if it is running 
# for too long.
CLUSTERING_PENDING_CACHE_TIME = 60*1

# Folder for saving the clustering results with evaluation (dev/debug/research purpose)
SAVE_RESULTS_FOLDER = None

# Limit of distance when creating Nearest Neighbors graph
MAX_NEIGHBORS_DISTANCE = 20

# Number of sound examples extracted per cluster for cluster facet sound preview
NUM_SOUND_EXAMPLES_PER_CLUSTER_FACET = 7

# Number of most common tags extracted per cluster for clustering facet name
NUM_TAGS_SHOWN_PER_CLUSTER_FACET = 3

# Number of maximum clusters to show to the user
NUM_MAX_CLUSTERS = 8
