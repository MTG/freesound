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
from django.conf import settings
from django.shortcuts import render, redirect, reverse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

import forms
import sounds
import forum
from utils.search.search_general import search_prepare_sort, search_process_filter, \
    search_prepare_query, perform_solr_query
from utils.logging_filters import get_client_ip
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
from utils.clustering_utilities import cluster_sound_results

logger = logging.getLogger("search")


def search(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    filter_query_link_more_when_grouping_packs = filter_query.replace(' ','+')
    cluster_id = request.GET.get('cluster_id', "")

    # Generate array with information of filters
    filter_query_split = []
    if filter_query != "":
        for filter_str in re.findall(r'[\w-]+:\"[^\"]+', filter_query):
            valid_filter = True
            filter_str = filter_str + '"'
            filter_display = filter_str.replace('"', '')
            filter_name = filter_str.split(":")[0]
            if filter_name != "duration" and filter_name != "is_geotagged":
                if filter_name == "grouping_pack":
                    val = filter_display.split(":")[1]
                    # If pack does not contain "_" then it's not a valid pack filter
                    if "_" in val:
                        filter_display = "pack:"+ val.split("_")[1]
                    else:
                        valid_filter = False

                if valid_filter:
                    filter = {
                        'name': filter_display,
                        'remove_url': filter_query.replace(filter_str, ''),
                    }
                    filter_query_split.append(filter)

    if cluster_id != "":  # cluster filter is in a separate query parameter
        filter_query_split.append({
            'name': "Cluster #" + cluster_id,
            'remove_url': filter_query,
        })

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    sort_unformatted = request.GET.get("s", None)
    sort_options = forms.SEARCH_SORT_OPTIONS_WEB
    grouping = request.GET.get("g", "1")  # Group by default

    # If the query is filtered by pack, do not collapse sounds of the same pack (makes no sense)
    # If the query is through AJAX (for sources remix editing), do not collapse
    if "pack" in filter_query or request.GET.get("ajax", "") == "1":
        grouping = ""

    # Set default values
    id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
    tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
    description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
    username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
    pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
    original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

    # Parse advanced search options
    advanced = request.GET.get("advanced", "")
    advanced_search_params_dict = {}

    # if advanced search
    if advanced == "1":
        a_tag = request.GET.get("a_tag", "")
        a_filename = request.GET.get("a_filename", "")
        a_description = request.GET.get("a_description", "")
        a_packname = request.GET.get("a_packname", "")
        a_soundid = request.GET.get("a_soundid", "")
        a_username = request.GET.get("a_username", "")
        advanced_search_params_dict.update({  # These are stored in a dict to facilitate logging and passing to template
            'a_tag': a_tag,
            'a_filename': a_filename,
            'a_description': a_description,
            'a_packname': a_packname,
            'a_soundid': a_soundid,
            'a_username': a_username,
        })

        # If none is selected use all (so other filter can be appleid)
        if a_tag or a_filename or a_description or a_packname or a_soundid or a_username != "" :

            # Initialize all weights to 0
            id_weight = 0
            tag_weight = 0
            description_weight = 0
            username_weight = 0
            pack_tokenized_weight = 0
            original_filename_weight = 0

            # Set the weights of selected checkboxes
            if a_soundid != "":
                id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
            if a_tag != "":
                tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
            if a_description != "":
                description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
            if a_username != "":
                username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
            if a_packname != "":
                pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
            if a_filename != "":
                original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

    sort = search_prepare_sort(sort_unformatted, forms.SEARCH_SORT_OPTIONS_WEB)

    logger.info(u'Search (%s)' % json.dumps({
        'ip': get_client_ip(request),
        'query': search_query,
        'filter': filter_query,
        'username': request.user.username,
        'page': current_page,
        'sort': sort[0],
        'group_by_pack': grouping,
        'advanced': json.dumps(advanced_search_params_dict) if advanced == "1" else ""
    }))

    # we send the query parameters in the context for clustering
    query_params = {
        'search_query': search_query,
        'filter_query': filter_query.replace('"', '\\"'),  # " can appear when filtering with facets
        'sort': sort,
        'current_page': current_page,
        'sounds_per_page': settings.SOUNDS_PER_PAGE,
        'id_weight': id_weight,
        'tag_weight': tag_weight,
        'description_weight': description_weight,
        'username_weight': username_weight,
        'pack_tokenized_weight': pack_tokenized_weight,
        'original_filename_weight': original_filename_weight,
        'grouping': grouping
    }

    # get sound ids of the requested cluster
    in_ids = get_ids_in_cluster(query_params, cluster_id)

    query = search_prepare_query(search_query,
                                 filter_query,
                                 sort,
                                 current_page,
                                 settings.SOUNDS_PER_PAGE,
                                 id_weight,
                                 tag_weight,
                                 description_weight,
                                 username_weight,
                                 pack_tokenized_weight,
                                 original_filename_weight,
                                 grouping=grouping,
                                 in_ids=in_ids,
                                 )

    tvars = {
        'error_text': None,
        'filter_query': filter_query,
        'filter_query_split': filter_query_split,
        'search_query': search_query,
        'grouping': grouping,
        'advanced': advanced,
        'sort': sort,
        'sort_unformatted': sort_unformatted,
        'sort_options': sort_options,
        'filter_query_link_more_when_grouping_packs': filter_query_link_more_when_grouping_packs,
        'current_page': current_page,
    }
    if advanced == "1":
        tvars.update(advanced_search_params_dict)

    try:
        non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
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
            'query_params': json.dumps(query_params),
        })

    except SolrException as e:
        logger.warning('Search error: query: %s error %s' % (query, e))
        tvars.update({'error_text': 'There was an error while searching, is your query correct?'})
    except Exception as e:
        logger.error('Could probably not connect to Solr - %s' % e)
        tvars.update({'error_text': 'The search server could not be reached, please try again later.'})

    if request.GET.get("ajax", "") != "1":
        return render(request, 'search/search.html', tvars)
    else:
        return render(request, 'search/search_ajax.html', tvars)


def get_ids_in_cluster(query_params, requested_cluster_id):
    if requested_cluster_id == "":
        return []
    else:
        requested_cluster_id = int(requested_cluster_id) - 1

        # results are cached in clustering_utilities
        results, num_clusters, _ = cluster_sound_results(query_params)

        # move this in clustering utilities
        sounds_from_requested_cluster = [str(sound_id) for sound_id, cluster_id in results.iteritems() 
                                         if cluster_id==requested_cluster_id]

        return sounds_from_requested_cluster


def cluster_sounds(request):
    query_params = json.loads(request.GET.get("query_params", ""))
    sort_unformatted = request.GET.get("sort_unformatted", "")

    results, num_clusters, _ = cluster_sound_results(query_params)

    num_sounds_per_cluster = [results.values().count(cluster_idx) for cluster_idx in range(num_clusters)]

    return render(request, 'search/clustering_facet.html', {
            'results': results,
            'query_params': query_params,
            'sort_unformatted': sort_unformatted,
            'cluster_id_num_results': zip(range(num_clusters), num_sounds_per_cluster),
    })


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
            logger.warning("search error: query: %s error %s" % (query, e))
            error = True
            error_text = 'There was an error while searching, is your query correct?'
        except Exception as e:
            logger.error("Could probably not connect to Solr - %s" % e)
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
