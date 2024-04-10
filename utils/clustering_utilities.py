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

from collections import defaultdict, Counter
import random

import celery
from django.conf import settings
from django.core.cache import caches
from django.urls import reverse

from clustering.tasks import cluster_sounds
import sounds
from utils.search.search_sounds import get_sound_similarity_from_search_engine_query, get_sound_ids_from_search_engine_query


cache_clustering = caches["clustering"]


def get_clusters_for_query(sqp, compute_if_not_in_cache=True):
    # Note we don't include facet filters in the generated params because we want to apply clustering "before" the rest of the facets 
    # (so clustering only depends on the search options specified in the form, but not the facet filters)
    query_params = sqp.as_query_params(exclude_facet_filters=True)  
    
    # get result from cache or perform clustering
    cache_key = sqp.get_clustering_data_cache_key()
    results = cache_clustering.get(cache_key, None)
    if results is None and compute_if_not_in_cache:
        # First get the similarity vectors for the first settings.MAX_RESULTS_FOR_CLUSTERING results from the query
        similarity_vectors_map = get_sound_similarity_from_search_engine_query(
            query_params, 
            analyzer_name=settings.CLUSTERING_SIMILARITY_ANALYZER,
            num_sounds=settings.MAX_RESULTS_FOR_CLUSTERING,
            current_page=1)        
        sound_ids = list(similarity_vectors_map.keys())
        if sound_ids:
            # Now launch the clustering celery task
            # Note that we launch the task synchronously (i.e. we block here until the task finishes). This is because this
            # view will be loaded asynchronously from the search page, and the clustering task should only take a few seconds.
            # If for some reason the clustering task takes longer and a timeout erorr is raised, that is fine as we'll simply
            # not show the clustering section.
            async_task_result = cluster_sounds.apply_async(kwargs={
                'cache_key': cache_key,
                'sound_ids': sound_ids,
                'similarity_vectors_map': similarity_vectors_map
            })
            try:
                results = async_task_result.get(timeout=settings.CLUSTERING_TASK_TIMEOUT)  # Will raise exception if task takes too long
            except celery.exceptions.TimeoutError as e:
                # Cancel the task so it stops running (or it never starts)
                async_task_result.revoke(terminate=True)
            if results['clusters'] is not None:
                # Generate cluster summaries (cluster names and sound examples)
                clusters = results['clusters']
                partition = {sound_id: cluster_id for cluster_id, cluster in enumerate(clusters) for sound_id in cluster}

                # label clusters using most occuring tags
                sound_instances = sounds.models.Sound.objects.bulk_query_id(list(map(int, list(partition.keys()))))
                sound_tags = {sound.id: sound.tag_array for sound in sound_instances}
                cluster_tags = defaultdict(list)

                # extract tags for each clusters and do not use query terms for labeling clusters
                query_terms = {t.lower() for t in sqp.options['query'].value.split(' ')}
                for sound_id, tags in sound_tags.items():
                    cluster_tags[partition[str(sound_id)]] += [t.lower() for t in tags if t.lower() not in query_terms]

                # count 3 most occuring tags
                # we iterate with range(len(clusters)) to ensure that we get the right order when iterating through the dict
                cluster_most_occuring_tags = [
                    [tag for tag, _ in Counter(cluster_tags[cluster_id]).most_common(settings.NUM_TAGS_SHOWN_PER_CLUSTER)]
                    if cluster_tags[cluster_id] else []
                    for cluster_id in range(len(clusters))
                ]
                most_occuring_tags_formatted = [
                    ' '.join(sorted(most_occuring_tags))
                    for most_occuring_tags in cluster_most_occuring_tags
                ]
                results['cluster_names'] = most_occuring_tags_formatted

                # select sound examples for each cluster
                sound_ids_examples_per_cluster = [
                    list(map(int, cluster_sound_ids[:settings.NUM_SOUND_EXAMPLES_PER_CLUSTER]))
                    for cluster_sound_ids in clusters
                ]
                sound_ids_examples = [item for sublist in sound_ids_examples_per_cluster for item in sublist]
                # TODO: collect some metadata for the sound examples and pass it to the template so we can display/play them
                example_sounds_data = range(len(sound_ids_examples))
                results['example_sounds_data'] = example_sounds_data

                # Generate random IDs for the clusters that will be used to identify them
                cluster_ids = [random.randint(0, 99999) for _ in range(len(clusters))]
                results['cluster_ids'] = cluster_ids
        else:
             # If no sounds to cluster, set to None
            results = {'clusters': None}

        # Save results in cache
        cache_clustering.set(cache_key, results, settings.CLUSTERING_CACHE_TIME)
    return results


def get_clustering_data_for_graph_display(sqp, initial_graph):
    cache_key = sqp.get_clustering_data_cache_key(include_filters_from_facets=True) + '-graph_display'
    graph = cache_clustering.get(cache_key, None)
    if graph is None:
        # If graph data is not in cache, we need to generate it
        # To compute the graph we need to know which sounds are still part of the set of results AFTER the
        # facet filters have been applied. To get this information we need to make a query to the search engine.
    
        # check if facet filters are present in the search query
        # if yes, filter nodes and links from the graph
        graph = initial_graph
        query_params = sqp.as_query_params()
        if len(sqp.non_option_filters):
            nodes = graph['nodes']
            links = graph['links']
            graph['nodes'] = []
            graph['links'] = []
            sound_ids_filtered = get_sound_ids_from_search_engine_query(query_params, num_sounds=settings.MAX_RESULTS_FOR_CLUSTERING, current_page=1)
            for node in nodes:
                if int(node['id']) in sound_ids_filtered:
                    graph['nodes'].append(node)
            for link in links:
                if int(link['source']) in sound_ids_filtered and int(link['target']) in sound_ids_filtered:
                    graph['links'].append(link)

        results = sounds.models.Sound.objects.bulk_query_id([int(node['id']) for node in graph['nodes']])
        sound_metadata = {}
        for sound in results:
            sound_locations = sound.locations()
            sound_metadata.update(
                {sound.id: (
                    sound_locations['preview']['LQ']['ogg']['url'],
                    sound.original_filename,
                    ' '.join(sound.tag_array),
                    reverse("sound", args=(sound.username, sound.id)),
                    sound_locations['display']['wave']['M']['url'],
                )}
            )

        for node in graph['nodes']:
            node['url'] = sound_metadata[int(node['id'])][0]
            node['name'] = sound_metadata[int(node['id'])][1]
            node['tags'] = sound_metadata[int(node['id'])][2]
            node['sound_page_url'] = sound_metadata[int(node['id'])][3]
            node['image_url'] = sound_metadata[int(node['id'])][4]
        cache_clustering.set(cache_key, graph, settings.CLUSTERING_CACHE_TIME)
    return graph


def get_num_sounds_per_cluster(sqp, clusters):
    cache_key = sqp.get_clustering_data_cache_key(include_filters_from_facets=True) + '-num_sounds'
    num_sounds_per_cluster = cache_clustering.get(cache_key, None)
    if num_sounds_per_cluster is None:
        if clusters:
            # To compute the number of sounds per cluster we need to know which sounds are still part of the set of results AFTER the
            # facet filters have been applied. To get this information we need to make a query to the search engine.
            query_params = sqp.as_query_params()
            if len(sqp.non_option_filters):
                sound_ids_filtered = get_sound_ids_from_search_engine_query(query_params, num_sounds=settings.MAX_RESULTS_FOR_CLUSTERING, current_page=1)
                clusters = [[sound_id for sound_id in cluster if int(sound_id) in sound_ids_filtered]
                        for cluster in clusters]
            num_sounds_per_cluster = [len(cluster) for cluster in clusters]
        else:
            num_sounds_per_cluster = []
        cache_clustering.set(cache_key, num_sounds_per_cluster, settings.CLUSTERING_CACHE_TIME)
    return num_sounds_per_cluster


def cluster_data_is_fully_available(sqp):
    cache_key = sqp.get_clustering_data_cache_key()
    if cache_clustering.get(cache_key, None) is None:
        return False
    cache_key_num_sounds = sqp.get_clustering_data_cache_key(include_filters_from_facets=True) + '-num_sounds'
    if cache_clustering.get(cache_key_num_sounds, None) is None:
        return False
    return True


def get_ids_in_cluster(cache_key, cluster_id):
    results = cache_clustering.get(cache_key, None)
    if results is not None:
        try:
            cluster_index = results['cluster_ids'].index(cluster_id)
            return results['clusters'][cluster_index]
        except (IndexError, ValueError, KeyError) as e:
            pass
    return []
