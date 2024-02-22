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

import datetime
import json
import logging
import re
import sentry_sdk
from collections import defaultdict, Counter

from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, reverse, render
from ratelimit.decorators import ratelimit

import forum
import sounds
import geotags
from clustering.clustering_settings import DEFAULT_FEATURES, NUM_SOUND_EXAMPLES_PER_CLUSTER_FACET, \
    NUM_TAGS_SHOWN_PER_CLUSTER_FACET
from clustering.interface import cluster_sound_results, get_sound_ids_from_search_engine_query
from forum.models import Post
from utils.encryption import create_hash
from utils.logging_filters import get_client_ip
from utils.ratelimit import key_for_ratelimiting, rate_per_ip
from utils.search.search_sounds import perform_search_engine_query
from utils.search import get_search_engine, SearchEngineException, SearchResultsPaginator, search_query_processor

search_logger = logging.getLogger("search")


def search_view_helper(request):
    # Process request data with the SearchQueryProcessor
    sqp = search_query_processor.SearchQueryProcessor(request)
    
    # Check if there was a filter parsing error and return error if so
    if sqp.errors:
        search_logger.info(f"Errors in SearchQueryProcessor: {sqp.errors}")
        return {'error_text': 'There was an error while searching, is your query correct?'}

    # Update compact mode prefernece if user has explicitely specified a different value than the preference
    if request.user.is_authenticated:
        option = sqp.options[search_query_processor.SearchOptionGridMode.name]
        if option.set_in_request:
            request_preference = option.value
            user_preference = request.user.profile.use_compact_mode
            if request_preference != user_preference:
                request.user.profile.use_compact_mode = request_preference
                request.user.profile.save()

    # Parpare variables for map view (prepare some URLs for loading sounds and providing links to map)
    open_in_map_url = None
    map_mode_query_results_cache_key = None
    map_bytearray_url = ''
    if sqp.map_mode:
        current_query_params = request.get_full_path().split("?")[-1]
        open_in_map_url = reverse('geotags-query') + f'?{current_query_params}'
        map_mode_query_results_cache_key = f'map-query-results-{create_hash(current_query_params, 10)}'
        map_bytearray_url = reverse('geotags-for-query-barray') + f'?key={map_mode_query_results_cache_key}'

    # If in tags mode and no tags in filter, return before making the query as we'll make
    # the initial tagcloud in tags.views.tags view and no need to make any further query here
    if sqp.tags_mode and not sqp.get_tags_in_filter():
        return {'sqp': sqp}  # sqp will be needed in tags.views.tags view

    # Run the query and post-process the results
    try:    
        query_params = sqp.as_query_params()    
        results, paginator = perform_search_engine_query(query_params)
        if not sqp.map_mode:
            if not sqp.display_as_packs:
                resultids = [d.get("id") for d in results.docs]
                resultsounds = sounds.models.Sound.objects.bulk_query_id(resultids)
                allsounds = {}
                for s in resultsounds:
                    allsounds[s.id] = s
                # allsounds will contain info from all the sounds returned by bulk_query_id. This should
                # be all sounds in docs, but if solr and db are not synchronised, it might happen that there
                # are ids in docs which are not found in bulk_query_id. To avoid problems we remove elements
                # in docs that have not been loaded in allsounds.
                docs = [doc for doc in results.docs if doc["id"] in allsounds]
                for d in docs:
                    d["sound"] = allsounds[d["id"]]

                # Add URLs to "more from this pack" in the result object so these are easily accessible in the template
                for d in docs:
                    if d.get("n_more_in_group") and d["sound"].pack_id is not None:
                        d["more_from_this_pack_url"] = sqp.get_url(add_filters=[f'grouping_pack:"{d["sound"].pack_id}_{d["sound"].pack_name}"'])
            else:
                resultspackids = []
                sound_ids_for_pack_id = {}
                for d in results.docs:
                    pack_id = int(d.get("group_name").split('_')[0])
                    resultspackids.append(pack_id)
                    sound_ids_for_pack_id[pack_id] = [int(sound['id']) for sound in d.get('group_docs', [])]
                resultpacks = sounds.models.Pack.objects.bulk_query_id(resultspackids, sound_ids_for_pack_id=sound_ids_for_pack_id)
                allpacks = {}
                for p in resultpacks:
                    allpacks[p.id] = p
                # allpacks will contain info from all the packs returned by bulk_query_id. This should
                # be all packs in docs, but if solr and db are not synchronised, it might happen that there
                # are ids in docs which are not found in bulk_query_id. To avoid problems we remove elements
                # in docs that have not been loaded in allsounds.
                docs = [d for d in results.docs if int(d.get("group_name").split('_')[0]) in allpacks]
                for d in docs:
                    d["pack"] = allpacks[int(d.get("group_name").split('_')[0])]
                    d["more_from_this_pack_url"] = sqp.get_url(add_filters=[f'grouping_pack:"{d["pack"].id}_{d["pack"].name}"'])
        else:
            # In map we configure the search query to already return geotags data. Here we collect all this data
            # and save it to the cache so we can collect it in the 'geotags_for_query_barray' view which prepares
            # data points for the map of sounds. 
            cache.set(map_mode_query_results_cache_key, results.docs, 60 * 15)  # cache for 5 minutes

            # Nevertheless we set docs to empty list as we won't displat anything in the search results page (the map
            # will make an extra request that will load the cached data and display it in the map)
            docs = []

        search_logger.info('Search (%s)' % json.dumps({
            'ip': get_client_ip(request),
            'query': query_params['textual_query'],
            'filter': query_params['query_filter'],
            'username': request.user.username,
            'page': query_params['current_page'],
            'sort': query_params['sort'],
            'url': sqp.get_url(),
            'tags_mode': sqp.tags_mode,
            'query_time': results.q_time 
        }))

        # For the facets of fields that could have mulitple values (i.e. currently, only "tags" facet), make
        # sure to remove the filters for the corresponding facet field that are already active (so we remove
        # redundant information)
        if 'tag' in results.facets:
            results.facets['tag'] = [(tag, count) for tag, count in results.facets['tag'] if tag not in sqp.get_tags_in_filter()]

        # Compile template variables
        return {
            'sqp': sqp,
            'error_text': None,
            'current_page': query_params['current_page'],
            'has_advanced_search_settings_set': sqp.contains_active_advanced_search_options(),
            'advanced_search_closed_on_load': settings.ADVANCED_SEARCH_MENU_ALWAYS_CLOSED_ON_PAGE_LOAD,
            'map_bytearray_url': map_bytearray_url,
            'open_in_map_url': open_in_map_url,
            'max_search_results_map_mode': settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,
            'paginator': paginator,
            'page': paginator.page(query_params['current_page']),
            'docs': docs,
            'facets': results.facets,
            'non_grouped_number_of_results': results.non_grouped_number_of_results,
        }

    except SearchEngineException as e:
        search_logger.info(f'Search error: query: {str(query_params)} error {e}')
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
        return {'error_text': 'There was an error while searching, is your query correct?'}
    except Exception as e:
        search_logger.info(f'Could probably not connect to Solr - {e}')
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
        return {'error_text': 'The search server could not be reached, please try again later.'}


@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SEARCH_GROUP, block=True)
def search(request):
    tvars = search_view_helper(request)

    current_query_params = request.get_full_path().split("?")[-1]
    get_cluster_url = reverse('clustering-section') + f'?{current_query_params}'

    tvars.update({'get_cluster_url': get_cluster_url})

    return render(request, 'search/search.html', tvars)


def clustering_section(request):
    """Triggers the computation of the clustering, returns the state of processing or the clustering facet.
    """

    result = cluster_sound_results(request)

    # check if computation is finished. If not, send computation state.
    if result['finished']:
        if result['result'] is not None:
            results = result['result']
            num_clusters = len(results)
        else:
             return JsonResponse({'status': 'failed'}, safe=False)
    elif result['error']:
        return JsonResponse({'status': 'failed'}, safe=False)
    else:
        return JsonResponse({'status': 'pending'}, safe=False)

    # check if facet filters are present in the search query
    # if yes, filter sounds from clusters
    sqp = search_query_processor.SearchQueryProcessor(request)
    query_params = sqp.as_query_params()
    if len(sqp.non_option_filters):
        sound_ids_filtered = get_sound_ids_from_search_engine_query(query_params)
        results = [[sound_id for sound_id in cluster if int(sound_id) in sound_ids_filtered]
                   for cluster in results]

    num_sounds_per_cluster = [len(cluster) for cluster in results]
    partition = {sound_id: cluster_id for cluster_id, cluster in enumerate(results) for sound_id in cluster}

    # label clusters using most occuring tags
    sound_instances = sounds.models.Sound.objects.bulk_query_id(list(map(int, list(partition.keys()))))
    sound_tags = {sound.id: sound.tag_array for sound in sound_instances}
    cluster_tags = defaultdict(list)

    # extract tags for each clusters and do not use query terms for labeling clusters
    query_terms = {t.lower() for t in request.GET.get('q', '').split(' ')}
    for sound_id, tags in sound_tags.items():
        cluster_tags[partition[str(sound_id)]] += [t.lower() for t in tags if t.lower() not in query_terms]

    # count 3 most occuring tags
    # we iterate with range(len(results)) to ensure that we get the right order when iterating through the dict
    cluster_most_occuring_tags = [
        [tag for tag, _ in Counter(cluster_tags[cluster_id]).most_common(NUM_TAGS_SHOWN_PER_CLUSTER_FACET)]
        if cluster_tags[cluster_id] else []
        for cluster_id in range(len(results))
    ]
    most_occuring_tags_formatted = [
        ' '.join(sorted(most_occuring_tags))
        for most_occuring_tags in cluster_most_occuring_tags
    ]

    # extract sound examples for each cluster
    sound_ids_examples_per_cluster = [
        list(map(int, cluster_sound_ids[:NUM_SOUND_EXAMPLES_PER_CLUSTER_FACET]))
        for cluster_sound_ids in results
    ]
    sound_ids_examples = [item for sublist in sound_ids_examples_per_cluster for item in sublist]
    sound_urls = {
        sound.id: sound.locations()['preview']['LQ']['ogg']['url']
            for sound in sound_instances
            if sound.id in sound_ids_examples
    }
    sound_url_examples_per_cluster = [
        [(sound_id, sound_urls[sound_id]) for sound_id in cluster_sound_ids]
            for cluster_sound_ids in sound_ids_examples_per_cluster
    ]

    current_query_params = request.get_full_path().split("?")[-1]
    get_cluster_url = reverse('geotags-query') + f'?{current_query_params}'

    return render(request, 'search/clustering_results.html', {
            'results': partition,
            'get_cluster_url': get_cluster_url,
            'cluster_id_num_results_tags_sound_examples': list(zip(
                list(range(num_clusters)),
                num_sounds_per_cluster,
                most_occuring_tags_formatted,
                sound_url_examples_per_cluster
            )),
    })


def clustered_graph(request):
    """Returns the clustered sound graph representation of the search results.
    """
    result = cluster_sound_results(request, features=DEFAULT_FEATURES)
    graph = result['graph']

    # check if facet filters are present in the search query
    # if yes, filter nodes and links from the graph
    sqp = search_query_processor.SearchQueryProcessor(request)
    query_params = sqp.as_query_params()
    if len(sqp.non_option_filters):
        nodes = graph['nodes']
        links = graph['links']
        graph['nodes'] = []
        graph['links'] = []
        sound_ids_filtered = get_sound_ids_from_search_engine_query(query_params)
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

    return JsonResponse(json.dumps(graph), safe=False)


def search_forum(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    current_forum_name_slug = request.GET.get("forum", "").strip()    # for context sensitive search
    if current_forum_name_slug:
        current_forum = get_object_or_404(forum.models.Forum.objects, name_slug=current_forum_name_slug)
    else:
        current_forum = None
    sort = settings.SEARCH_FORUM_SORT_DEFAULT

    # Get username filter if any and prepare URL to remove the filter
    # NOTE: the code below is not robust to more complex filters. To do that we should do proper parsing
    # of the filters like we do for the search view
    username_filter = None
    remove_username_filter_url = ''
    if 'post_author' in filter_query:
        username_filter = filter_query.split('post_author:"')[1].split('"')[0]
        remove_username_filter_url = '{}?{}'.format(reverse('forums-search'), filter_query.replace('post_author:"{}"'.format(username_filter), ''))
        sort = settings.SEARCH_FORUM_SORT_OPTION_DATE_NEW_FIRST
    
    # Parse advanced search options
    advanced_search = request.GET.get("advanced_search", "")
    date_from = request.GET.get("dt_from", "")
    try:
        df_parsed = datetime.datetime.strptime(date_from, "%Y-%m-%d")
        date_from_display = df_parsed.strftime("%d-%m-%Y")
    except ValueError:
        date_from = ""
        date_from_display = "Choose a Date"
    date_to = request.GET.get("dt_to", "")
    try:
        dt_parsed = datetime.datetime.strptime(date_to, "%Y-%m-%d")
        date_to_display = dt_parsed.strftime("%d-%m-%Y")
    except ValueError:
        date_to = ""
        date_to_display = "Choose a Date"

    if search_query.startswith("search in"):
        search_query = ""

    error = False
    error_text = ""
    paginator = None
    num_results = None
    page = None
    results = []
    if search_query.strip() != "" or filter_query:
        # add current forum
        if current_forum:
            filter_query += "forum_name_slug:" + current_forum.name_slug

        # add date range
        if advanced_search == "1" and date_from != "" or date_to != "":
            filter_query = __add_date_range(filter_query, date_from, date_to)

        try:
            results = get_search_engine().search_forum_posts(
                textual_query=search_query,
                query_filter=filter_query,
                sort=sort,
                num_posts=settings.FORUM_POSTS_PER_PAGE,
                current_page=current_page,
                group_by_thread=False)

            paginator = SearchResultsPaginator(results, settings.FORUM_POSTS_PER_PAGE)
            num_results = paginator.count
            page = paginator.page(current_page)
            error = False
        except SearchEngineException as e:
            error.info(f"Search error: query: {search_query} error {e}")
            sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
            error = True
            error_text = 'There was an error while searching, is your query correct?'
        except Exception as e:
            search_logger.info(f"Could probably not connect to the search engine - {e}")
            sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
            error = True
            error_text = 'The search server could not be reached, please try again later.'


    tvars = {
        'advanced_search': advanced_search,
        'current_forum': current_forum,
        'current_page': current_page,
        'date_from': date_from,
        'date_from_display': date_from_display,
        'date_to': date_to,
        'date_to_display': date_to_display,
        'error': error,
        'error_text': error_text,
        'filter_query': filter_query,
        'username_filter': username_filter,
        'remove_username_filter_url': remove_username_filter_url,
        'num_results': num_results,
        'page': page,
        'paginator': paginator,
        'search_query': search_query,
        'sort': sort,
        'results': results
    }

    if results:
        posts_unsorted = Post.objects.select_related('thread', 'thread__forum', 'author', 'author__profile')\
            .filter(id__in=[d['id'] for d in results.docs])
        posts_map = {post.id:post for post in posts_unsorted}
        posts = [posts_map[d['id']] for d in results.docs]            
    else:
        posts = []
    tvars.update({
        'posts': posts
    })

    return render(request, 'search/search_forum.html', tvars)


def __add_date_range(filter_query, date_from, date_to):
    if filter_query != "":
        filter_query += " "
    filter_query += "thread_created:["
    date_from = date_from + "T00:00:00Z" if date_from != "" else "*"
    date_to = date_to + "T00:00:00Z]" if date_to != "" else "*]"
    return filter_query + date_from + " TO " + date_to


def query_suggestions(request):
    # TODO: implement this. We can use Solr's SpellCheckComponent see https://github.com/MTG/freesound/issues/510
    # query suggestions can be enabled and disabled via settings.ENABLE_QUERY_SUGGESTIONS
    suggestions = []
    search_query = request.GET.get('q', None)
    if search_query is not None and len(search_query) > 1:
        for count, suggestion in enumerate([
            'wind',
            'explosion',
            'music',
            'rain',
            'swoosh'
        ]):
            suggestions.append({'id': count, 'value': suggestion})
    return JsonResponse({'suggestions': suggestions})
