from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from utils.search.search import *

logger = logging.getLogger("search")

def search(request):
    search_query = request.GET.get("q")
    filter_query = request.GET.get("f", "")

    sort = request.GET.get("s", None)
    if sort:
        sort = [sort]

    current_page = int(request.GET.get("page", 1))

    solr = Solr("http://localhost:8983/solr/")
    
    query = SolrQuery()
    query.set_dismax_query(search_query, query_fields=[("id", 4), ("tag",3), ("description",3), ("username",2), ("pack_original",2), ("filename",2), "comment"])
    query.set_query_options(start=(current_page - 1) * settings.SOUNDS_PER_PAGE, rows=settings.SOUNDS_PER_PAGE, field_list=["id"], filter_query=filter_query, sort=sort)
    query.add_facet_fields("samplerate", "pack_original", "username", "tag", "bitrate", "bitdepth", "type", "channels")
    query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=False)
    query.set_facet_options("tag", limit=30)
    query.set_facet_options("username", limit=30)
    query.set_facet_options("pack_original", limit=10)
    
    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results)
        page = paginator.page(current_page)
        error = False
    except SolrException, e:
        logger.warning("search error: search_query %s filter_query %s sort %s error %s" % (search_query, filter_query, sort, e))
        error = True
    
    return render_to_response('search/search.html', locals(), context_instance=RequestContext(request))
