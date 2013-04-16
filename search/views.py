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

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
from datetime import datetime
import forms
import logging

logger = logging.getLogger("search")
logger_click = logging.getLogger('clickusage')

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
        sort = [forms.SEARCH_DEFAULT_SORT]
    return sort

DEFAULT_SEARCH_WEIGHTS = {
                        'id' : 4,
                        'tag' : 4,
                        'description' : 3,
                        'username' : 1,
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
                         original_filename_weight = DEFAULT_SEARCH_WEIGHTS['original_filename'],
                         grouping = False):
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
                           query_fields=field_weights,)
    query.set_query_options(start=(current_page - 1) * sounds_per_page, rows=sounds_per_page, field_list=["id"], filter_query=filter_query, sort=sort)
    query.add_facet_fields("samplerate", "grouping_pack", "username", "tag", "bitrate", "bitdepth", "type", "channels", "license")
    query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=False)
    query.set_facet_options("tag", limit=30)
    query.set_facet_options("username", limit=30)
    query.set_facet_options("grouping_pack", limit=10)
    query.set_facet_options("license", limit=10)

    if grouping:
        query.set_group_field(group_field="grouping_pack")
        query.set_group_options(group_func=None,
            group_query=None,
            group_rows=10,
            group_start=0,
            group_limit=1,
            group_offset=0,
            group_sort=None,
            group_sort_ingroup=None,
            group_format='grouped',
            group_main=False,
            group_num_groups=True,
            group_cache_percent=0)


    return query

def search(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    filter_query_link_more_when_grouping_packs = filter_query.replace(' ','+')

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    sort = request.GET.get("s", None)
    sort_options = forms.SEARCH_SORT_OPTIONS_WEB


    grouping = request.GET.get("g", "1") # Group by default
    actual_groupnig = grouping
    # If the query is filtered by pack, do not collapse sounds of the same pack (makes no sense)
    # If the query is thourhg ajax (for sources remix editing), do not collapse
    if "pack" in filter_query or request.GET.get("ajax", "") == "1":
        actual_groupnig = ""

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

    # ALLOW "q" empty queries
    #if search_query.strip() == ""

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
                                 original_filename_weight,
                                 grouping = actual_groupnig
                                 )
    
    solr = Solr(settings.SOLR_URL) 
        
    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
        num_results = paginator.count
        non_grouped_number_of_results = results.non_grouped_number_of_matches
        page = paginator.page(current_page)
        error = False
       
        # clickusage tracking           
        if settings.LOG_CLICKTHROUGH_DATA:
            # If the user reformulates the query, add it to the query chain
            request.session.setdefault("query_chain", [])
            if search_query not in request.session["query_chain"]:
                request.session["query_chain"].append(search_query.encode("utf-8"))
            # The session id of an unauthenticated user is different from the session id of the same user when
            # authenticated.
            if not request.user.is_authenticated():
                request.session["anonymous_session_key"]=request.session.session_key
            else:
                request.session["anonymous_session_key"]=""
            request.session["current_page"] = current_page
            if results.docs is not None:
                ids = []
                for item in results.docs:
                    ids.append(item["id"])
                request.session["current_page_ranks"] = ids

    except SolrException, e:
        logger.warning("search error: query: %s error %s" % (query, e))
        error = True
        error_text = 'There was an error while searching, is your query correct?'
    except Exception, e:
        print e
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
    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    current_forum_name_slug = request.GET.get("current_forum_name_slug", "").strip()    # for context sensitive search
    current_forum_name = request.GET.get("current_forum_name", "").strip()              # used in breadcrumb  
    sort = ["thread_created asc"]
    
    # Parse advanced search options
    advanced_search = request.GET.get("advanced_search", "")
    date_from = request.GET.get("dt_from", "")
    date_to = request.GET.get("dt_to", "")
    
    # TEMPORAL WORKAROUND!!! to prevent using watermark as the query for forum search.. (in only happens in some situations)
    if "search in " in search_query :
        invalid = 1
    
    if search_query.strip() != "":
        # add current forum
        if current_forum_name_slug.strip() != "":
            filter_query =  "forum_name_slug:" + current_forum_name_slug
            
        # add date range
        if advanced_search == "1" and date_from != "" or date_to != "":
            filter_query = __add_date_range(filter_query, date_from, date_to)
        
        query = SolrQuery()
        query.set_dismax_query(search_query, query_fields=[("thread_title", 4), ("post_body",3), ("thread_author",3), ("forum_name",2)])
        query.set_highlighting_options_default(field_list=["post_body"],
                                               fragment_size=200, 
                                               alternate_field="post_body", # TODO: revise this param
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
        query.set_group_options(group_limit=3)
        
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

def __add_date_range(filter_query, date_from, date_to):
    if filter_query != "":
        filter_query += " "
    
    filter_query += "thread_created:["
    date_from = date_from + "T00:00:00Z" if date_from != "" else "*"
    date_to = date_to + "T00:00:00Z]" if date_to != "" else "*]"
    
    return filter_query + date_from + " TO " + date_to
