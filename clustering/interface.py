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
from __future__ import absolute_import
from builtins import str
from django.conf import settings
from django.core.cache import caches

from .clustering_settings import DEFAULT_FEATURES, MAX_RESULTS_FOR_CLUSTERING
from freesound.celery import app as celery_app
from utils.encryption import create_hash
from utils.search.backends.solr555pysolr import SOLR_VECTOR_FIELDS_DIMENSIONS_MAP
from utils.search.search_sounds import perform_search_engine_query
from utils.search import search_query_processor
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED

cache_clustering = caches["clustering"]

def hash_cache_key(key):
    return create_hash(key, limit=32)


def get_sound_ids_from_search_engine_query(query_params):
    """Performs Solr query and returns results as a list of sound ids.

    This method performs a single query to Solr with a very big page size argument so all results are 
    returned at once. A very big page size will make the clustering take a lot of time to be performed.
    The number of results to retrieve is defined in the clustering settings file as MAX_RESULTS_FOR_CLUSTERING.

    Args:
        query_params (dict): contains the query parameters to replicate the user query.
    
    Returns
        List[int]: list containing the ids of the retrieved sounds.
    """
    # We set include_facets to False in order to reduce the amount of data that search engine will return.
    query_params.update({
        'current_page': 1,
        'num_sounds': MAX_RESULTS_FOR_CLUSTERING,
    })
    results, _ = perform_search_engine_query(query_params)
    resultids = [d.get("id") for d in results.docs]

    return resultids


def cluster_sound_results(request):
    """Performs clustering on the search results of the given search request with the requested features.

    This is the main entry to the clustering method. It will either get the clustering results from cache, 
    or compute it (and store it in cache). When needed, the clustering will be performed async by a celery 
    worker. 

    Args:
        request (HttpRequest): request associated with the search query submitted by the user.

    Returns:
        Dict: contains either the state of the clustering ('pending' or 'failed') or the resulting clustering classes 
            and the graph in node-link format suitable for JSON serialization.
    """
    sqp = search_query_processor.SearchQueryProcessor(request)
    query_params = sqp.as_query_params(exclude_facet_filters=True)  # Note we don't include facet filters in the generated params because we want to apply clustering "before" the rest of the facets (so clustering only depends on the search options specified in the form, but not the facet filters)
    
    cache_key = 'cluster-results-{textual_query}-{query_filter}-{sort}-{group_by_pack}'\
        .format(**query_params).replace(' ', '')
    cache_key += f"-{str(query_params['query_fields'])}"
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
        analyzer_name = settings.CLUSTERING_SIMILARITY_ANALYZER   
        config_options = settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS[analyzer_name]
        vector_field_name = SOLR_VECTOR_FIELDS_DIMENSIONS_MAP.get(config_options['vector_size'])
        query_params.update({
            'facets': None,
            'current_page': 1,
            'num_sounds': MAX_RESULTS_FOR_CLUSTERING,
            'field_list': ['id', 'score', 'similarity_vectors', 'sim_vector100', f'[child childFilter="content_type:v AND analyzer:{analyzer_name}" limit=1]']
        })
        results, _ = perform_search_engine_query(query_params)

        # Collect sound IDs and similarity vectors from query results
        similarity_vectors_map = {}
        for d in results.docs:
            if 'group_docs' in d:
                d0 = d['group_docs'][0]
            else:
                d0 = d
            if len(d0.get("similarity_vectors", [])) > 0:
                similarity_vectors_map[d0['id']] = d0["similarity_vectors"][0][vector_field_name]
        sound_ids = list(similarity_vectors_map.keys())

        # launch clustering with celery async task
        celery_app.send_task('cluster_sounds', kwargs={
            'cache_key_hashed': cache_key_hashed,
            'sound_ids': sound_ids,
            'similarity_vectors_map': similarity_vectors_map
        }, queue='clustering')

        return {'finished': False, 'error': False}


def get_ids_in_cluster(request, requested_cluster_id):
    """Get the sound ids in the requested cluster. Used for applying a filter by id when using a cluster facet.
    """
    try:
        requested_cluster_id = int(requested_cluster_id) - 1

        # results are cached in clustering_utilities, available features are defined in the clustering settings file.
        result = cluster_sound_results(request, features=DEFAULT_FEATURES)
        results = result['result']

        sounds_from_requested_cluster = results[int(requested_cluster_id)]

    except ValueError:
        return []
    except IndexError:
        return []
    except KeyError:
        # If the clustering is not in cache the 'result' key won't exist
        # This means that the clustering computation will be triggered asynchronously.
        # Moreover, the applied clustering filter will have no effect.
        # Somehow, we should inform the user that the clustering results were not available yet, and that
        # he should try again later to use a clustering facet.
        return []

    return sounds_from_requested_cluster


