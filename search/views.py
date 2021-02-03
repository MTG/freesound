
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
from collections import defaultdict, Counter

import re
from django.conf import settings
from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

import sounds
import forum
from utils.search.search_general import search_prepare_sort, search_process_filter, \
    search_prepare_query, perform_solr_query, search_prepare_parameters, split_filter_query
from utils.logging_filters import get_client_ip
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
from clustering.interface import cluster_sound_results, get_sound_ids_from_solr_query
from clustering.clustering_settings import DEFAULT_FEATURES, NUM_SOUND_EXAMPLES_PER_CLUSTER_FACET, \
    NUM_TAGS_SHOWN_PER_CLUSTER_FACET

search_logger = logging.getLogger("search")


def search(request):
    query_params, advanced_search_params_dict, extra_vars = search_prepare_parameters(request)

    # get the url query params for later sending it to the clustering engine
    url_query_params_string = request.META['QUERY_STRING']

    # get sound ids of the requested cluster when applying a clustering facet
    # the list of ids is used to create a Solr query with filter by ids in search_prepare_query()
    cluster_id = request.GET.get('cluster_id')

    if settings.ENABLE_SEARCH_RESULTS_CLUSTERING and cluster_id:
        in_ids = _get_ids_in_cluster(request, cluster_id)
    else:
        in_ids = []
    query_params.update({'in_ids': in_ids})

    filter_query_split = split_filter_query(query_params['filter_query'], cluster_id)

    tvars = {
        'error_text': None,
        'filter_query': query_params['filter_query'],
        'filter_query_split': filter_query_split,
        'search_query': query_params['search_query'],
        'grouping': query_params['grouping'],
        'advanced': extra_vars['advanced'],
        'sort': query_params['sort'],
        'sort_unformatted': extra_vars['sort_unformatted'],
        'sort_options': extra_vars['sort_options'],
        'filter_query_link_more_when_grouping_packs': extra_vars['filter_query_link_more_when_grouping_packs'],
        'current_page': query_params['current_page'],
        'url_query_params_string': url_query_params_string,
        'cluster_id': extra_vars['cluster_id'],
    }
    
    tvars.update(advanced_search_params_dict)

    search_logger.info(u'Search (%s)' % json.dumps({
        'ip': get_client_ip(request),
        'query': query_params['search_query'],
        'filter': query_params['filter_query'],
        'username': request.user.username,
        'page': query_params['current_page'],
        'sort': query_params['sort'][0],
        'group_by_pack': query_params['grouping'],
        'advanced': json.dumps(advanced_search_params_dict) if extra_vars['advanced'] == "1" else ""
    }))

    query = search_prepare_query(**query_params)

    try:
        non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, 
                                                                                          query_params['current_page'])
        resultids = [d.get("id") for d in docs]
        resultsounds = sounds.models.Sound.objects.bulk_query_id(resultids)
        allsounds = {}
        for s in resultsounds:
            allsounds[s.id] = s
        # allsounds will contain info from all the sounds returned by bulk_query_id. This should
        # be all sounds in docs, but if solr and db are not synchronised, it might happen that there
        # are ids in docs which are not found in bulk_query_id. To avoid problems we remove elements
        # in docs that have not been loaded in allsounds.
        docs = [doc for doc in docs if doc["id"] in allsounds]
        for d in docs:
            d["sound"] = allsounds[d["id"]]
        
        tvars.update({
            'paginator': paginator,
            'page': page,
            'docs': docs,
            'facets': facets,
            'non_grouped_number_of_results': non_grouped_number_of_results,
        })

    except SolrException as e:
        search_logger.warning('Search error: query: %s error %s' % (query, e))
        tvars.update({'error_text': 'There was an error while searching, is your query correct?'})
    except Exception as e:
        search_logger.error('Could probably not connect to Solr - %s' % e)
        tvars.update({'error_text': 'The search server could not be reached, please try again later.'})

    # enables AJAX clustering call & html clustering facets rendering
    if settings.ENABLE_SEARCH_RESULTS_CLUSTERING:
        tvars.update({'clustering_on': "true"})

    if request.GET.get("ajax", "") != "1":
        return render(request, 'search/search.html', tvars)
    else:
        return render(request, 'search/search_ajax.html', tvars)


def _get_ids_in_cluster(request, requested_cluster_id):
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
        sound_ids_filtered = get_sound_ids_from_solr_query(query_params)
        results = [[sound_id for sound_id in cluster if int(sound_id) in sound_ids_filtered] 
                   for cluster in results]

    num_sounds_per_cluster = [len(cluster) for cluster in results]
    partition = {sound_id: cluster_id for cluster_id, cluster in enumerate(results) for sound_id in cluster}

    # label clusters using most occuring tags
    sound_instances = sounds.models.Sound.objects.bulk_query_id(map(int, partition.keys()))
    sound_tags = {sound.id: sound.tag_array for sound in sound_instances}
    cluster_tags = defaultdict(list)

    # extract tags for each clusters and do not use query terms for labeling clusters
    query_terms = {t.lower() for t in request.GET.get('q', '').split(' ')}
    for sound_id, tags in sound_tags.iteritems():
        cluster_tags[partition[str(sound_id)]] += [t.lower() for t in tags if t.lower() not in query_terms]

    # count 3 most occuring tags
    # we iterate with range(len(results)) to ensure that we get the right order when iterating through the dict 
    cluster_most_occuring_tags = [
        [tag for tag, _ in Counter(cluster_tags[cluster_id]).most_common(NUM_TAGS_SHOWN_PER_CLUSTER_FACET)]
        if cluster_tags[cluster_id] else []
        for cluster_id in range(len(results))
    ]
    most_occuring_tags_formatted = [
        ' '.join(most_occuring_tags) 
        for most_occuring_tags in cluster_most_occuring_tags
    ]

    # extract sound examples for each cluster
    sound_ids_examples_per_cluster = [
        map(int, cluster_sound_ids[:NUM_SOUND_EXAMPLES_PER_CLUSTER_FACET]) 
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
            'cluster_id_num_results_tags_sound_examples': zip(
                range(num_clusters), 
                num_sounds_per_cluster, 
                most_occuring_tags_formatted, 
                sound_url_examples_per_cluster
            ),
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
        sound_ids_filtered = get_sound_ids_from_solr_query(query_params)
        for node in nodes:
            if int(node['id']) in sound_ids_filtered:
                graph['nodes'].append(node)
        for link in links:
            if int(link['source']) in sound_ids_filtered and int(link['target']) in sound_ids_filtered:
                graph['links'].append(link)

    results = sounds.models.Sound.objects.bulk_query_id([int(node['id']) for node in graph['nodes']])

    sound_metadata = {s.id:(s.locations()['preview']['LQ']['ogg']['url'],
                            s.original_filename,
                            ' '.join(s.tag_array),
                            s.get_absolute_url(),
                            s.locations()['display']['wave']['M']['url']) for s in results}

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
    sort = ["thread_created desc"]

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

        query = SolrQuery()
        query.set_dismax_query(search_query, query_fields=[("thread_title", 4),
                                                           ("post_body", 3),
                                                           ("thread_author", 3),
                                                           ("post_author", 3),
                                                           ("forum_name", 2)])
        query.set_highlighting_options_default(field_list=["post_body"],
                                               fragment_size=200,
                                               alternate_field="post_body",  # TODO: revise this param
                                               require_field_match=False,
                                               pre="<strong>",
                                               post="</strong>")
        query.set_query_options(start=(current_page - 1) * settings.SOUNDS_PER_PAGE,
                                rows=settings.SOUNDS_PER_PAGE,
                                field_list=["id",
                                            "forum_name",
                                            "forum_name_slug",
                                            "thread_id",
                                            "thread_title",
                                            "thread_author",
                                            "thread_created",
                                            "post_body",
                                            "post_author",
                                            "post_created",
                                            "num_posts"],
                                filter_query=filter_query,
                                sort=sort)

        query.set_group_field("thread_title_grouped")
        query.set_group_options(group_limit=30)

        solr = Solr(settings.SOLR_FORUM_URL)

        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
            num_results = paginator.count
            page = paginator.page(current_page)
            error = False
        except SolrException as e:
            search_logger.warning("search error: query: %s error %s" % (query, e))
            error = True
            error_text = 'There was an error while searching, is your query correct?'
        except Exception as e:
            search_logger.error("Could probably not connect to Solr - %s" % e)
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
        'num_results': num_results,
        'page': page,
        'paginator': paginator,
        'search_query': search_query,
        'sort': sort,
        'results': results,
    }

    return render(request, 'search/search_forum.html', tvars)


def get_pack_tags(pack_obj):
    query = SolrQuery()
    query.set_dismax_query('')
    filter_query = 'username:\"%s\" pack:\"%s\"' % (pack_obj.user.username, pack_obj.name)
    query.set_query_options(field_list=["id"], filter_query=filter_query)
    query.add_facet_fields("tag")
    query.set_facet_options("tag", limit=20, mincount=1)
    try:
        solr = Solr(settings.SOLR_URL)
        results = SolrResponseInterpreter(solr.select(unicode(query)))
    except (SolrException, Exception) as e:
        #  TODO: do something here?
        return False
    return results.facets


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
            suggestions.append({'id': count, 'label': '<p>{0}</p>'.format(suggestion), 'value': suggestion})
    return JsonResponse({'suggestions': suggestions})
