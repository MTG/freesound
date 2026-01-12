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
import traceback

import sentry_sdk
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, reverse
from django_ratelimit.decorators import ratelimit

import forum
import sounds
from forum.models import Post
from utils.clustering_utilities import (
    cluster_data_is_fully_available,
    get_clustering_data_for_graph_display,
    get_clusters_for_query,
    get_num_sounds_per_cluster,
)
from utils.encryption import create_hash
from utils.logging_filters import get_client_ip
from utils.ratelimit import key_for_ratelimiting, rate_per_ip
from utils.search import SearchEngineException, SearchResultsPaginator, get_search_engine, search_query_processor
from utils.search.search_sounds import (
    allow_beta_search_features,
    get_empty_query_cache_key,
    perform_search_engine_query,
)

search_logger = logging.getLogger("search")


def is_empty_query(request):
    # Check if the request correpsonds to an empty query with all the default parameters. It happens when the user
    # hits "enter" in the search box without entering any text. This can be used to return cached results for this common
    # case which typically produces long queries
    return len(request.GET) == 0 or (len(request.GET) == 1 and "q" in request.GET and request.GET["q"] == "")


def search_view_helper(request):
    # Process request data with the SearchQueryProcessor
    sqp = search_query_processor.SearchQueryProcessor(request)
    use_beta_features = allow_beta_search_features(request)

    # Check if there was a filter parsing error and return error if so
    if sqp.errors:
        search_logger.info(f"Errors in SearchQueryProcessor: {sqp.errors}")
        return {"error_text": "There was an error while searching, is your query correct?"}

    # Update compact mode preference if user has explicitly specified a different value than the preference
    if request.user.is_authenticated:
        option = sqp.options["grid_mode"]
        if option.set_in_request:
            request_preference = option.value
            user_preference = request.user.profile.use_compact_mode
            if request_preference != user_preference:
                request.user.profile.use_compact_mode = request_preference
                request.user.profile.save()

    # Prepare variables for map view (prepare some URLs for loading sounds and providing links to map)
    open_in_map_url = None
    map_mode_query_results_cache_key = None
    map_bytearray_url = ""
    if sqp.map_mode_active():
        current_query_params = request.get_full_path().split("?")[-1]
        open_in_map_url = reverse("geotags-query") + f"?{current_query_params}"
        map_mode_query_results_cache_key = f"map-query-results-{create_hash(current_query_params, 10)}"
        map_bytearray_url = reverse("geotags-for-query-barray") + f"?key={map_mode_query_results_cache_key}"

    # Prepare variables for clustering
    get_clusters_url = None
    clusters_data = None
    if sqp.compute_clusters_active() and use_beta_features:
        if cluster_data_is_fully_available(sqp):
            # If clustering data for the current query is fully available, we can get it directly
            clusters_data = _get_clusters_data_helper(sqp)
        else:
            # Otherwise pass the url where the cluster data fill be fetched asynchronously from
            get_clusters_url = reverse("clusters-section") + f"?{request.get_full_path().split('?')[-1]}"

    # If in tags mode and no tags in filter, return before making the query as we'll make
    # the initial tagcloud in tags.views.tags view and no need to make any further query here
    if sqp.tags_mode_active() and not sqp.get_tags_in_filters():
        return {"sqp": sqp}  # sqp will be needed in tags.views.tags view

    # Run the query and post-process the results
    try:
        query_params = {}  # Initialize to avoid reference before assignment if exception occurs at sqp.as_query_params()
        query_params = sqp.as_query_params()

        empty_query_cache_key = get_empty_query_cache_key(request, use_beta_features=use_beta_features)
        if is_empty_query(request) and empty_query_cache_key:
            # This common case produces long queries but the results will change very slowly (only when we index new sounds),
            # so we can cache them.
            results_paginator = cache.get(empty_query_cache_key, None)
            if results_paginator is not None:
                # If results are cached, we use them directly
                results, paginator = results_paginator
                results.q_time = None  # Set query time to None as we are not actually querying the search engine
            else:
                # Perform the query and cache the results
                results, paginator = perform_search_engine_query(query_params)
                cache.set(empty_query_cache_key, (results, paginator), settings.SEARCH_EMPTY_QUERY_CACHE_TIME)

        else:
            # Perform the query normally
            results, paginator = perform_search_engine_query(query_params)

        if sqp.map_mode_active():
            # In map we configure the search query to already return geotags data. Here we collect all this data
            # and save it to the cache so we can collect it in the 'geotags_for_query_barray' view which prepares
            # data points for the map of sounds.
            cache.set(map_mode_query_results_cache_key, results.docs, 60 * 15)  # cache for 15 minutes

            # Nevertheless we set docs to empty list as we won't display anything in the search results page (the map
            # will make an extra request that will load the cached data and display it in the map)
            docs = []
        else:
            if not sqp.display_as_packs_active():
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
                        d["more_from_this_pack_url"] = sqp.get_url(
                            add_filters=[f'pack_grouping:"{d["sound"].pack_id}_{d["sound"].pack.name}"']
                        )
            else:
                resultspackids = []
                sound_ids_for_pack_id = {}
                for d in results.docs:
                    pack_id = int(d.get("group_name").split("_")[0])
                    resultspackids.append(pack_id)
                    sound_ids_for_pack_id[pack_id] = [int(sound["id"]) for sound in d.get("group_docs", [])]
                resultpacks = sounds.models.Pack.objects.bulk_query_id(
                    resultspackids, sound_ids_for_pack_id=sound_ids_for_pack_id
                )
                allpacks = {}
                for p in resultpacks:
                    allpacks[p.id] = p
                # allpacks will contain info from all the packs returned by bulk_query_id. This should
                # be all packs in docs, but if solr and db are not synchronised, it might happen that there
                # are ids in docs which are not found in bulk_query_id. To avoid problems we remove elements
                # in docs that have not been loaded in allsounds.
                docs = [d for d in results.docs if int(d.get("group_name").split("_")[0]) in allpacks]
                for d in docs:
                    d["pack"] = allpacks[int(d.get("group_name").split("_")[0])]
                    d["more_from_this_pack_url"] = sqp.get_url(
                        add_filters=[f'pack_grouping:"{d["pack"].id}_{d["pack"].name}"']
                    )

        search_logger.info(
            "Search (%s)"
            % json.dumps(
                {
                    "ip": get_client_ip(request),
                    "query": query_params["textual_query"],
                    "filter": query_params["query_filter"],
                    "username": request.user.username,
                    "page": query_params["current_page"],
                    "sort": query_params["sort"],
                    "url": sqp.get_url(),
                    "tags_mode": sqp.tags_mode_active(),
                    "query_time": results.q_time,
                }
            )
        )

        # Compile template variables
        return {
            "sqp": sqp,
            "error_text": None,
            "current_page": query_params["current_page"],
            "has_advanced_search_settings_set": sqp.contains_active_advanced_search_options(),
            "advanced_search_closed_on_load": settings.ADVANCED_SEARCH_MENU_ALWAYS_CLOSED_ON_PAGE_LOAD,
            "map_bytearray_url": map_bytearray_url,
            "open_in_map_url": open_in_map_url,
            "max_search_results_map_mode": settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,
            "get_clusters_url": get_clusters_url,
            "clusters_data": clusters_data,
            "paginator": paginator,
            "page": paginator.page(query_params["current_page"]),
            "docs": docs,
            "facets": results.facets,
            "non_grouped_number_of_results": results.non_grouped_number_of_results,
            "show_beta_search_options": use_beta_features,
            "experimental_facets": settings.SEARCH_SOUNDS_BETA_FACETS,
        }

    except SearchEngineException as e:
        search_logger.info(f"Search error: query: {str(query_params)} error {e}")
        sentry_sdk.capture_exception(e)
        return {"error_text": "There was an error while searching, is your query correct?"}
    except Exception as e:
        stack_trace = traceback.format_exc()
        search_logger.info(f"Could probably not connect to Solr - {e}\n{stack_trace}")
        sentry_sdk.capture_exception(e)
        return {"error_text": "The search server could not be reached, please try again later."}


@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SEARCH_GROUP, block=True)
def search(request):
    tvars = search_view_helper(request)
    return render(request, "search/search.html", tvars)


def _get_clusters_data_helper(sqp):
    # Get main cluster data
    results = get_clusters_for_query(sqp)
    if results is None:
        return None

    # Get the number of sounds per cluster
    # This number depends on the facet filters which are applied AFTER the main clustering.
    # See get_num_sounds_per_cluster for more details.
    num_sounds_per_cluster = get_num_sounds_per_cluster(sqp, results["clusters"])

    # Return a list with information for each cluster
    # Note that this information DOES NOT include the actual sound IDs per cluster.
    return list(
        zip(
            results.get("cluster_ids", []),  # cluster ID
            num_sounds_per_cluster,  # Num sounds
            results.get("cluster_names", []),  # Cluster name
            results.get("example_sounds_data", []),  # Example sounds
        )
    )


def clusters_section(request):
    sqp = search_query_processor.SearchQueryProcessor(request)
    clusters_data = _get_clusters_data_helper(sqp)
    if clusters_data is None:
        return render(request, "search/clustering_results.html", {"clusters_data": None})
    return render(request, "search/clustering_results.html", {"sqp": sqp, "clusters_data": clusters_data})


def clustered_graph(request):
    """Returns the clustered sound graph representation of the search results."""
    # TODO: this view is currently not used in the new UI, but we could add a modal in the
    # clustering section to show results in a graph.
    sqp = search_query_processor.SearchQueryProcessor(request)
    results = get_clusters_for_query(sqp)
    if results is None:
        JsonResponse(json.dumps({"error": True}), safe=False)
    graph = get_clustering_data_for_graph_display(sqp, results["graph"])
    return JsonResponse(json.dumps(graph), safe=False)


def search_forum(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    current_forum_name_slug = request.GET.get("forum", "").strip()  # for context sensitive search
    if current_forum_name_slug:
        current_forum = get_object_or_404(forum.models.Forum.objects, name_slug=current_forum_name_slug)
    else:
        current_forum = None
    sort = settings.SEARCH_FORUM_SORT_DEFAULT

    # Get username filter if any and prepare URL to remove the filter
    # NOTE: the code below is not robust to more complex filters. To do that we should do proper parsing
    # of the filters like we do for the search view
    username_filter = None
    remove_username_filter_url = ""
    if "post_author" in filter_query:
        username_filter = filter_query.split('post_author:"')[1].split('"')[0]
        remove_username_filter_url = "{}?{}".format(
            reverse("forums-search"), filter_query.replace(f'post_author:"{username_filter}"', "")
        )
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
                group_by_thread=False,
            )

            paginator = SearchResultsPaginator(results, settings.FORUM_POSTS_PER_PAGE)
            num_results = paginator.count
            page = paginator.page(current_page)
            error = False
        except SearchEngineException as e:
            search_logger.info(f"Search error: query: {search_query} error {e}")
            sentry_sdk.capture_exception(e)
            error = True
            error_text = "There was an error while searching, is your query correct?"
        except Exception as e:
            search_logger.info(f"Could probably not connect to the search engine - {e}")
            sentry_sdk.capture_exception(e)
            error = True
            error_text = "The search server could not be reached, please try again later."

    tvars = {
        "advanced_search": advanced_search,
        "current_forum": current_forum,
        "current_page": current_page,
        "date_from": date_from,
        "date_from_display": date_from_display,
        "date_to": date_to,
        "date_to_display": date_to_display,
        "error": error,
        "error_text": error_text,
        "filter_query": filter_query,
        "username_filter": username_filter,
        "remove_username_filter_url": remove_username_filter_url,
        "num_results": num_results,
        "page": page,
        "paginator": paginator,
        "search_query": search_query,
        "sort": sort,
        "results": results,
    }

    if results:
        post_ids = [int(d["id"]) for d in results.docs]
        posts_unsorted = Post.objects.select_related("thread", "thread__forum", "author", "author__profile").filter(
            id__in=post_ids
        )
        posts_map = {post.id: post for post in posts_unsorted}
        posts = [posts_map[id] for id in post_ids]
    else:
        posts = []
    tvars.update({"posts": posts})

    return render(request, "search/search_forum.html", tvars)


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
    search_query = request.GET.get("q", None)
    if search_query is not None and len(search_query) > 1:
        for count, suggestion in enumerate(["wind", "explosion", "music", "rain", "swoosh"]):
            suggestions.append({"id": count, "value": suggestion})
    return JsonResponse({"suggestions": suggestions})
