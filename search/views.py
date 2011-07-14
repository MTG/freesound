from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
import logging
import forms

logger = logging.getLogger("search")

def search_prepare_sort(sort, options):
    """ for ordering by rating order by rating, then by number of ratings """
    if sort in [x[1] for x in options]:
        if sort == "avg_rating desc":
            sort = [sort, "num_ratings desc"]
        elif  sort == "avg_rating asc":
            sort = [sort, "num_ratings asc"]
        else:
            sort = [sort]
    else:
        sort = ["num_downloads desc"]
    return sort

DEFAULT_SEARCH_WEIGHTS = {
                        'id' : 4,
                        'tag' : 3,
                        'description' : 3,
                        'username' : 2,
                        'pack_tokenized' : 2,
                        'original_filename' : 2
                        }

def search_prepare_query(search_query,
                         filter_query,
                         sort,
                         current_page,
                         sounds_per_page,
                         id_weight = DEFAULT_SEARCH_WEIGHTS['id'],
                         tag_weight = DEFAULT_SEARCH_WEIGHTS['tag'],
                         description_weight = DEFAULT_SEARCH_WEIGHTS['description'],
                         username_weight = DEFAULT_SEARCH_WEIGHTS['username'],
                         pack_tokenized_weight = DEFAULT_SEARCH_WEIGHTS['pack_tokenized'],
                         original_filename_weight = DEFAULT_SEARCH_WEIGHTS['original_filename']):
    query = SolrQuery()

    field_weights = []
    if id_weight != 0 :
        field_weights.append(("id", id_weight))
    if tag_weight != 0 :
        field_weights.append(("tag", tag_weight))
    if description_weight != 0 :
        field_weights.append(("description", description_weight))
    if username_weight != 0 :
        field_weights.append(("username", username_weight))
    if pack_tokenized_weight != 0 :
        field_weights.append(("pack_tokenized", pack_tokenized_weight))
    if original_filename_weight != 0 :
        field_weights.append(("original_filename", original_filename_weight))

    query.set_dismax_query(search_query,
                           query_fields=field_weights)
    query.set_query_options(start=(current_page - 1) * sounds_per_page, rows=sounds_per_page, field_list=["id"], filter_query=filter_query, sort=sort)
    query.add_facet_fields("samplerate", "pack", "username", "tag", "bitrate", "bitdepth", "type", "channels", "license")
    query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=False)
    query.set_facet_options("tag", limit=30)
    query.set_facet_options("username", limit=30)
    query.set_facet_options("pack", limit=10)
    query.set_facet_options("license", limit=10)
    return query

def search(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    current_page = int(request.GET.get("page", 1))
    sort = request.GET.get("s", forms.SEARCH_DEFAULT_SORT)
    sort_options = forms.SEARCH_SORT_OPTIONS_WEB

    # Set default values
    id_weight = DEFAULT_SEARCH_WEIGHTS['id']
    tag_weight = DEFAULT_SEARCH_WEIGHTS['tag']
    description_weight = DEFAULT_SEARCH_WEIGHTS['description']
    username_weight = DEFAULT_SEARCH_WEIGHTS['username']
    pack_tokenized_weight = DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
    original_filename_weight = DEFAULT_SEARCH_WEIGHTS['original_filename']

    # Parse advanced search options
    advanced = request.GET.get("advanced", "")

    # if advanced search
    if advanced == "1" :
        a_tag = request.GET.get("a_tag", "")
        a_filename = request.GET.get("a_filename", "")
        a_description = request.GET.get("a_description", "")
        a_packname = request.GET.get("a_packname", "")
        a_soundid = request.GET.get("a_soundid", "")
        a_username = request.GET.get("a_username", "")

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
            if a_soundid != "" :
                id_weight = DEFAULT_SEARCH_WEIGHTS['id']
            if a_tag != "" :
                tag_weight = DEFAULT_SEARCH_WEIGHTS['tag']
            if a_description != "" :
                description_weight = DEFAULT_SEARCH_WEIGHTS['description']
            if a_username != "" :
                username_weight = DEFAULT_SEARCH_WEIGHTS['username']
            if a_packname != "" :
                pack_tokenized_weight = DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
            if a_filename != "" :
                original_filename_weight = DEFAULT_SEARCH_WEIGHTS['original_filename']

    # Allow to return ALL sounds when search has no q parameter
    #if search_query.strip() != "":
    sort = search_prepare_sort(sort, forms.SEARCH_SORT_OPTIONS_WEB)

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
                                 original_filename_weight
                                 )
    
    solr = Solr(settings.SOLR_URL) 
        
    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
        num_results = paginator.count
        page = paginator.page(current_page)
        error = False
    except SolrException, e:
        logger.warning("search error: query: %s error %s" % (query, e))
        error = True
        error_text = 'There was an error while searching, is your query correct?'
    except Exception, e:
        logger.error("Could probably not connect to Solr - %s" % e)
        error = True
        error_text = 'The search server could not be reached, please try again later.'

    if request.GET.get("ajax", "") != "1":
        return render_to_response('search/search.html', locals(), context_instance=RequestContext(request))
    else:
        return render_to_response('search/search_ajax.html', locals(), context_instance = RequestContext(request))

def search_forum(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    current_page = int(request.GET.get("page", 1))
    current_forum_name_slug = request.GET.get("current_forum_name_slug", "").strip()    # for context sensitive search
    current_forum_name = request.GET.get("current_forum_name", "").strip()              # used in breadcrumb  
    sort = ["thread_created asc"]
    
    if search_query.strip() != "":
        if current_forum_name_slug.strip() != "":
            filter_query =  "forum_name_slug:" + current_forum_name_slug

        query = SolrQuery()
        query.set_dismax_query(search_query, query_fields=[("thread_title", 4), ("post_body",3), ("thread_author",3), ("forum_name",2)])
        query.set_highlighting_options_default(field_list=["post_body"],
                                               fragment_size=200, 
                                               alternate_field="post_body", # TODO: revise this param
                                               require_field_match=False, 
                                               pre="<strong>", 
                                               post="</strong>")
        query.set_query_options(start=(current_page - 1) * 30,
                                rows=30, 
                                field_list=["id", 
                                            "forum_name",
                                            "forum_name_slug",
                                            "thread_id", 
                                            "thread_title", 
                                            "thread_author", 
                                            "post_body",
                                            "post_username", 
                                            "thread_created",
                                            "num_posts"],
                                filter_query=filter_query, 
                                sort=sort)
        
        query.set_group_field("thread_title")
        query.set_group_options(group_limit=1)
        
        solr = Solr(settings.SOLR_FORUM_URL) 
        
        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
            num_results = paginator.count
            page = paginator.page(current_page)
            error = False
        except SolrException, e:
            logger.warning("search error: query: %s error %s" % (query, e))
            error = True
            error_text = 'There was an error while searching, is your query correct?'
        except Exception, e:
            logger.error("Could probably not connect to Solr - %s" % e)
            error = True
            error_text = 'The search server could not be reached, please try again later.'
    else:
        results = []
    
    return render_to_response('search/search_forum.html', locals(), context_instance=RequestContext(request))


def get_pack_tags(pack_obj):
    query = SolrQuery()
    query.set_dismax_query('')
    #filter_query = 'username:\"%s\" pack:\"%s\"' % (pack_obj.user.username, pack_obj.name)
    filter_query = 'pack:\"%s\"' % (pack_obj.name,)
    query.set_query_options(field_list=["id"], filter_query=filter_query)
    query.add_facet_fields("tag")
    query.set_facet_options("tag", limit=20, mincount=1)
    solr = Solr(settings.SOLR_URL)

    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
    except SolrException, e:
        #logger.warning("search error: query: %s error %s" % (query, e))
        #error = True
        #error_text = 'There was an error while searching, is your query correct?'
        return False
    except Exception, e:
        #logger.error("Could probably not connect to Solr - %s" % e)
        #error = True
        #error_text = 'The search server could not be reached, please try again later.'
        return False

    return results.facets


