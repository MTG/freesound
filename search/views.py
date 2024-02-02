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
from utils.logging_filters import get_client_ip
from utils.ratelimit import key_for_ratelimiting, rate_per_ip
from utils.search.search_sounds import perform_search_engine_query, search_prepare_parameters, \
    split_filter_query, should_use_compact_mode, contains_active_advanced_search_filters
from utils.search import get_search_engine, SearchEngineException, SearchResultsPaginator

search_logger = logging.getLogger("search")


def search_view_helper(request, tags_mode=False):
    query_params, advanced_search_params_dict, extra_vars = search_prepare_parameters(request)

    # Check if there was a filter parsing error
    if extra_vars['parsing_error']:
        search_logger.info(f"Query filter parsing error. filter: {request.GET.get('f', '')}")
        extra_vars.update({'error_text': 'There was an error while searching, is your query correct?'})
        return extra_vars

    # Get the url query params for later sending it to the clustering engine (this is only used with the clustering feature)
    url_query_params_string = request.META['QUERY_STRING']

    # Get a "split" version of the filter which is used to display filters in UI and for some other checks (see below)
    filter_query_split = split_filter_query(query_params['query_filter'], extra_vars['parsed_filters'], extra_vars['cluster_id'])
    
    # Get tags taht are being used in filters (this is used later to remove them from the facet and also for tags mode)
    tags_in_filter = []
    for filter_data in filter_query_split:
        if filter_data['name'].startswith('tag:'):
            tag = filter_data['name'].replace('tag:', '')
            if tag.startswith('"'):
                # If tag name has quotes, remove them
                tag = tag[1:-1]
            tags_in_filter.append(tag)
    
    # Process tags mode stuff
    initial_tagcloud = None
    if tags_mode:
        # In tags mode, we increase the size of the tags facet so we include more related tags
        query_params['facets'][settings.SEARCH_SOUNDS_FIELD_TAGS]['limit'] = 50

        # If no tags are in filter, we are "starting" tag-based browsing so display the initial tagcloud
        if not tags_in_filter:
            initial_tagcloud = cache.get('initial_tagcloud')
            if initial_tagcloud is None:
                # If tagcloud is not cached, make a query to retrieve it and save it to cache
                results, _ = perform_search_engine_query(dict(
                    textual_query='',
                    query_filter= "*:*",
                    num_sounds=1,
                    facets={settings.SEARCH_SOUNDS_FIELD_TAGS: {'limit': 100}},
                    group_by_pack=True,
                    group_counts_as_one_in_facets=False,
                ))
                initial_tagcloud = [dict(name=f[0], count=f[1], browse_url=reverse('tags', args=[f[0]])) for f in results.facets["tag"]]
                cache.set('initial_tagcloud', initial_tagcloud, 60 * 60 * 12)  # cache for 12 hours
            return {
                'tags_mode': True,
                'tags_in_filter': tags_in_filter,
                'initial_tagcloud': initial_tagcloud,
            }

    # In the tvars section we pass the original group_by_pack value to avoid it being set to false if there is a pack filter (see search_prepare_parameters)
    # This is so that we keep track of the original setting of group_by_pack before the filter was applied, and so that if the pack filter is removed, we can 
    # automatically revert to the previous group_by_pack setting. Also, we compute "disable_group_by_pack_option" so that when we have changed the real
    # group_by_pack because there is a pack filter, we can grey out the option in the search form. Similar thing we do for only_sounds_with_pack as also
    # it does not make sense when filtering by pack
    group_by_pack_in_request = request.GET.get("g", "1") == "1"
    only_sounds_with_pack_in_request = request.GET.get("only_p", "0") == "1"
    disable_group_by_pack_option = 'pack:' in query_params['query_filter'] or only_sounds_with_pack_in_request
    disable_only_sounds_by_pack_option= 'pack:' in query_params['query_filter']
    only_sounds_with_pack = "1" if query_params['only_sounds_with_pack'] else ""
    if only_sounds_with_pack:
        # If displaying search results as packs, include 3 sounds per pack group in the results so we can display these sounds as selected sounds in the
        # display_pack templatetag
        query_params['num_sounds_per_pack_group'] = 3

    # Parpare variables for map view
    disable_display_results_in_grid_option = False
    map_bytearray_url = ''
    use_map_mode = settings.SEARCH_ALLOW_DISPLAY_RESULTS_IN_MAP and request.GET.get("mm", "0") == "1"
    if use_map_mode:
        disable_group_by_pack_option = True
        disable_only_sounds_by_pack_option = True
        disable_display_results_in_grid_option = True
        geotags.views.update_query_params_for_map_query(query_params, preserve_facets=True)
        map_bytearray_url = reverse('geotags-for-query-barray') + '?' + request.get_full_path().split('?')[-1]

    tvars = {
        'error_text': None,
        'filter_query': query_params['query_filter'],
        'filter_query_split': filter_query_split,
        'search_query': query_params['textual_query'],
        'similar_to': query_params['similar_to'],
        'group_by_pack_in_request': "1" if group_by_pack_in_request else "", 
        'disable_group_by_pack_option': disable_group_by_pack_option,
        'only_sounds_with_pack': only_sounds_with_pack,
        'only_sounds_with_pack_in_request': "1" if only_sounds_with_pack_in_request else "",
        'disable_only_sounds_by_pack_option': disable_only_sounds_by_pack_option,
        'use_compact_mode': should_use_compact_mode(request),
        'advanced': extra_vars['advanced'],
        'sort': query_params['sort'],
        'sort_options': [(option, option) for option in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB],
        'filter_query_link_more_when_grouping_packs': extra_vars['filter_query_link_more_when_grouping_packs'],
        'current_page': query_params['current_page'],
        'url_query_params_string': url_query_params_string,
        'cluster_id': extra_vars['cluster_id'],
        'clustering_on': settings.ENABLE_SEARCH_RESULTS_CLUSTERING,
        'weights': extra_vars['raw_weights_parameter'],
        'initial_tagcloud': initial_tagcloud,
        'tags_mode': tags_mode,
        'tags_in_filter': tags_in_filter,
        'has_advanced_search_settings_set': contains_active_advanced_search_filters(request, query_params, extra_vars),
        'advanced_search_closed_on_load': settings.ADVANCED_SEARCH_MENU_ALWAYS_CLOSED_ON_PAGE_LOAD,
        'allow_map_mode': settings.SEARCH_ALLOW_DISPLAY_RESULTS_IN_MAP,
        'use_map_mode': use_map_mode,
        'map_bytearray_url': map_bytearray_url,
        'disable_display_results_in_grid_option': disable_display_results_in_grid_option,
        'max_search_results_map_mode': settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY
    }
    tvars.update(advanced_search_params_dict)

    try:       
        results, paginator = perform_search_engine_query(query_params)
        if not use_map_mode:
            if not only_sounds_with_pack:
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
        else:
            # In map mode we don't need to retrieve any information about sounds as we'll make another query
            # to generate the geotags bytearray
            docs = []

        search_logger.info('Search (%s)' % json.dumps({
            'ip': get_client_ip(request),
            'query': query_params['textual_query'],
            'filter': query_params['query_filter'],
            'username': request.user.username,
            'page': query_params['current_page'],
            'sort': query_params['sort'],
            'group_by_pack': query_params['group_by_pack'],
            'advanced': json.dumps(advanced_search_params_dict) if extra_vars['advanced'] == "1" else "",
            'query_time': results.q_time 
        }))

        # For the facets of fields that could have mulitple values (i.e. currently, only "tags" facet), make
        # sure to remove the filters for the corresponding facet field thar are already active (so we remove
        # redundant information)
        if tags_in_filter:
            if 'tag' in results.facets:
                results.facets['tag'] = [(tag, count) for tag, count in results.facets['tag'] if tag not in tags_in_filter]

        tvars.update({
            'paginator': paginator,
            'page': paginator.page(query_params['current_page']),
            'docs': docs,
            'facets': results.facets,
            'non_grouped_number_of_results': results.non_grouped_number_of_results,
        })

    except SearchEngineException as e:
        search_logger.info(f'Search error: query: {str(query_params)} error {e}')
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
        tvars.update({'error_text': 'There was an error while searching, is your query correct?'})
    except Exception as e:
        search_logger.info(f'Could probably not connect to Solr - {e}')
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly
        tvars.update({'error_text': 'The search server could not be reached, please try again later.'})

    return tvars


@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SEARCH_GROUP, block=True)
def search(request):
    tvars = search_view_helper(request, tags_mode=False)
    template = 'search/search.html' if request.GET.get("ajax", "") != "1" else 'search/search_ajax.html'
    return render(request, template, tvars)


def clustering_facet(request):
    """Triggers the computation of the clustering, returns the state of processing or the clustering facet.
    """
    # pass the url query params for later sending it to the clustering engine
    url_query_params_string = request.META['QUERY_STRING']
    # remove existing cluster facet filter from the params since the returned cluster facets will include
    # their correspondinng cluster_id query parameter (done in the template)
    url_query_params_string = re.sub(r"(&cluster_id=[0-9]*)", "", url_query_params_string)

    result = cluster_sound_results(request, features=DEFAULT_FEATURES)

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
    query_params, _, extra_vars = search_prepare_parameters(request)
    if extra_vars['has_facet_filter']:
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

    return render(request, 'search/clustering_facet.html', {
            'results': partition,
            'url_query_params_string': url_query_params_string,
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
    query_params, _, extra_vars = search_prepare_parameters(request)
    if extra_vars['has_facet_filter']:
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
