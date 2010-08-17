from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
import operator
import logging

logger = logging.getLogger("search")
    
SEARCH_SORT_OPTIONS_WEB = [
        ("Duration (long first)"," duration desc"),
        ("Duration (short first)", "duration asc"),
        ("Date added (newest first)", "created desc"),
        ("Date added (oldest first)", "created asc"),
        ("Downloads (most first)", "num_downloads desc"),
        ("Downloads (least first)", "num_downloads asc"),
        ("Rating (highest first)", "avg_rating desc"),
        ("Rating (lowest first)", "avg_rating asc")
    ]

SEARCH_SORT_OPTIONS_API = [
        ("duration_desc"," duration desc"),
        ("duration_asc", "duration asc"),
        ("created_desc", "created desc"),
        ("created_asc", "created asc"),
        ("downloads_desc", "num_downloads desc"),
        ("downloads_asc", "num_downloads asc"),
        ("rating_desc", "avg_rating desc"),
        ("rating_asc", "avg_rating asc")
    ]

SEARCH_DEFAULT_SORT = "num_downloads desc"

def search_prepare_sort(sort, options):
    if sort in [x[1] for x in SEARCH_SORT_OPTIONS_WEB]:
        if sort == "avg_rating desc":
            sort = [sort, "avg_ratings desc"]
        elif  sort == "avg_rating asc":
            sort = [sort, "avg_ratings desc"]
        else:
            sort = [sort]
    else:
        sort = ["num_downloads desc"]
    return sort

settings.SOUNDS_PER_PAGE

def search_prepare_query(search_query, filter_query, sort, current_page, sounds_per_page):
    query = SolrQuery()
    query.set_dismax_query(search_query, query_fields=[("id", 4), ("tag",3), ("description",3), ("username",2), ("pack_tokenized",2), ("filename",2), "comment"])
    query.set_query_options(start=(current_page - 1) * sounds_per_page, rows=sounds_per_page, field_list=["id"], filter_query=filter_query, sort=sort)
    query.add_facet_fields("samplerate", "pack", "username", "tag", "bitrate", "bitdepth", "type", "channels")
    query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=False)
    query.set_facet_options("tag", limit=30)
    query.set_facet_options("username", limit=30)
    query.set_facet_options("pack", limit=10)
    return query

def search(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    current_page = int(request.GET.get("page", 1))
    sort = request.GET.get("s", SEARCH_DEFAULT_SORT)
    
    sort = search_prepare_sort(sort, SEARCH_SORT_OPTIONS_WEB)

    solr = Solr(settings.SOLR_URL)
    
    query = search_prepare_query(search_query, filter_query, sort, current_page, settings.SOUNDS_PER_PAGE)
    
    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
        page = paginator.page(current_page)
        error = False
    except SolrException, e:
        logger.warning("search error: search_query %s filter_query %s sort %s error %s" % (search_query, filter_query, sort, e))
        error = True
    
    return render_to_response('search/search.html', locals(), context_instance=RequestContext(request))
