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

from django.core.cache import caches

from clustering_settings import DEFAULT_FEATURES, MAX_RESULTS_FOR_CLUSTERING
from tasks import cluster_sounds
from utils.encryption import create_hash
from utils.search.search_general import search_prepare_query, perform_solr_query, \
    search_prepare_parameters
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED

cache_clustering = caches["clustering"]


def get_sound_ids_from_solr_query(query_params):
    """Performs Solr query and returns results as a list of sound ids.

    This method performs a single query to Solr with a very big page size argument so all results are 
    returned at once. A very big page size will make the clustering take a lot of time to be performed.
    The number of results to retrieve is defined in the clustering settings file as MAX_RESULTS_FOR_CLUSTERING.

    Args:
        query_params (dict): contains the query parameters to replicate the user query.
    
    Returns
        List[int]: list containing the ids of the retrieved sounds.
    """
    # We set include_facets to False in order to reduce the amount of data that Solr will return.
    query_params.update({
        'current_page': 1,
        'sounds_per_page': MAX_RESULTS_FOR_CLUSTERING,
        'include_facets': False,
    })
    query = search_prepare_query(**query_params)
    _, _, _, _, docs = perform_solr_query(query, query_params['current_page'])

    resultids = [d.get("id") for d in docs]
    return resultids


def cluster_sound_results(request, features=DEFAULT_FEATURES):
    """Performs clustering on the search results of the given search request with the requested features.

    This is the main entry to the clustering method. It will either get the clustering results from cache, 
    or compute it (and store it in cache). When needed, the clustering will be performed async by a celery 
    worker. 

    Args:
        request (HttpRequest): request associated with the search query submited by the user.
        features (str): name of the features to be used for clustering. The available features are defined in the 
            clustering settings file.

    Returns:
        Dict: contains either the state of the clustering ('pending' or 'failed') or the resulting clustering classes 
            and the graph in node-link format suitable for JSON serialization.
    """
    query_params, _, extra_vars = search_prepare_parameters(request)
    # We change filter_query to filter_query_non_facets in order to ensure that the clustering is always
    # done on the non faceted filtered results. Without that, people directly requesting a facet filtered
    # page would have a clustering performed on filtered results.
    query_params['filter_query'] = extra_vars['filter_query_non_facets']
    cache_key = 'cluster-results-{search_query}-{filter_query}-{sort}-{tag_weight}-{username_weight}-{id_weight}-' \
                '{description_weight}-{pack_tokenized_weight}-{original_filename_weight}-{grouping}'.format(**query_params) \
                .replace(' ', '')

    cache_key += '-{}'.format(features)
    cache_key_hashed = hash_cache_key(cache_key)

    # check if result is in cache
    result = cache_clustering.get(cache_key_hashed)

    if result and result not in (CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED):
        result.update({'finished': True, 'error': False})
        return result

    elif result == CLUSTERING_RESULT_STATUS_PENDING:
        return {'finished': False, 'error': False}

    elif result == CLUSTERING_RESULT_STATUS_FAILED:
        return {'finished': False, 'error': True}

    else:
        # if not in cache, query solr and perform clustering
        sound_ids = get_sound_ids_from_solr_query(query_params)

        # launch clustering with celery async task
        cluster_sounds.delay(cache_key_hashed, sound_ids, features)

        return {'finished': False, 'error': False}


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
