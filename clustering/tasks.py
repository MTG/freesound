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

from django.conf import settings
from celery import shared_task
from celery import Task

from .clustering import ClusteringEngine

class ClusteringTask(Task):
    """ Task Class used  for defining the clustering engine only required in celery workers    
    """
    def __init__(self):
        self.engine = ClusteringEngine()
            

@shared_task(name="cluster_sounds", base=ClusteringTask, queue=settings.CELERY_CLUSTERING_TASK_QUEUE_NAME)
def cluster_sounds(cache_key, sound_ids, similarity_vectors_map=None):
    """ Triggers the clustering of the sounds given as argument with the provided similarity vectors.
    The clustering result is stored in cache using the hashed cache key built with the query parameters.

    Args:
        cache_key (str): hashed key for storing/retrieving the results in cache.
        sound_ids (List[int]): list containing the ids of the sound to cluster.
        similarity_vectors_map (Dict{int:List[float]}): dictionary with the similarity feature vectors for each sound.
    """
    return cluster_sounds.engine.cluster_points(cache_key, sound_ids, similarity_vectors_map=similarity_vectors_map)
