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
from django.shortcuts import render
from django.template import RequestContext
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException
from utils.logging_filters import get_client_ip
import sounds
import forms
import logging
import json

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


def search_prepare_query(search_query,
                         filter_query,
                         sort,
                         current_page,
                         sounds_per_page,
                         id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id'],
                         tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag'],
                         description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description'],
                         username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username'],
                         pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized'],
                         original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename'],
                         grouping = False,
                         include_facets = True,
                         grouping_pack_limit = 1,
                         offset = None):
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
    if not offset:
        start = (current_page - 1) * sounds_per_page
    else:
        start = offset
    query.set_query_options(start=start, rows=sounds_per_page, field_list=["id"], filter_query=filter_query, sort=sort)

    if include_facets:
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
            group_limit=grouping_pack_limit,  # This is the number of documents that will be returned for each group. By default only 1 is returned.
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
    id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
    tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
    description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
    username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
    pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
    original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

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
                id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
            if a_tag != "" :
                tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
            if a_description != "" :
                description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
            if a_username != "" :
                username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
            if a_packname != "" :
                pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
            if a_filename != "" :
                original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

    # ALLOW "q" empty queries
    #if search_query.strip() == ""

    sort = search_prepare_sort(sort, forms.SEARCH_SORT_OPTIONS_WEB)

    logger.info(u'Search (%s)' % json.dumps({
        'ip': get_client_ip(request),
        'query': search_query,
        'filter': filter_query,
        'username': request.user.username,
        'page': current_page,
        'sort': sort[0],
        'group_by_pack' : actual_groupnig,
        'advanced': json.dumps({
            'search_in_tag': a_tag,
            'search_in_filename': a_filename,
            'search_in_description': a_description,
            'search_in_packname': a_packname,
            'search_in_soundid': a_soundid,
            'search_in_username': a_username
        }) if advanced == "1" else ""
    }))

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

    results = None
    docs = None
    error_text = None
    paginator = None
    num_results = None
    non_grouped_number_of_results = None
    page = None
    allsounds = {}
    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
        num_results = paginator.count
        non_grouped_number_of_results = results.non_grouped_number_of_matches
        page = paginator.page(current_page)
        error = False

        docs = results.docs
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

        # clickusage tracking
        if settings.LOG_CLICKTHROUGH_DATA:
            request_full_path = request.get_full_path()
            # The session id of an unauthenticated user is different from the session id of the same user when
            # authenticated.
            request.session["searchtime_session_key"] = request.session.session_key
            if results.docs is not None:
                ids = []
                for item in results.docs:
                    ids.append(item["id"])
            logger_click.info("QUERY : %s : %s : %s : %s" %
                                (unicode(request_full_path).encode('utf-8'), request.session.session_key, unicode(ids).encode('utf-8'), unicode(current_page).encode('utf-8')))

    except SolrException, e:
        logger.warning("search error: query: %s error %s" % (query, e))
        error = True
        error_text = 'There was an error while searching, is your query correct?'
    except Exception, e:
        print e
        logger.error("Could probably not connect to Solr - %s" % e)
        error = True
        error_text = 'The search server could not be reached, please try again later.'

    tvars = {
        'results': results,
        'docs': docs,
        'current_page': current_page,
        'error': error,
        'error_text': error_text,
        'paginator': paginator,
        'num_results': num_results,
        'non_grouped_number_of_results': non_grouped_number_of_results,
        'page': page,
        'allsounds': allsounds,
    }
    if request.GET.get("ajax", "") != "1":
        return render(request, 'search/search.html', tvars)
    else:
        return render(request, 'search/search_ajax.html', tvars)

def search_forum(request):
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "")
    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    current_forum_name_slug = request.GET.get("current_forum_name_slug", "").strip()    # for context sensitive search
    current_forum_name = request.GET.get("current_forum_name", "").strip()              # used in breadcrumb
    sort = ["thread_created desc"]

    # Parse advanced search options
    advanced_search = request.GET.get("advanced_search", "")
    date_from = request.GET.get("dt_from", "")
    date_to = request.GET.get("dt_to", "")

    # TEMPORAL WORKAROUND!!! to prevent using watermark as the query for forum search...
    # It only happens in some situations.
    if "search in " in search_query:
        invalid = 1

    if search_query.strip() != "" or filter_query:
        # add current forum
        if current_forum_name_slug.strip() != "":
            filter_query += "forum_name_slug:" + current_forum_name_slug

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

        error_text = None
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

    tvars = {
        'results': results,
        'paginator': paginator,
        'num_results': num_results,
        'page': page,
        'error' : error,
        'error_text': error_text
    }
    return render(request, 'search/search_forum.html', tvars)


def get_pack_tags(pack_obj):
    query = SolrQuery()
    query.set_dismax_query('')
    filter_query = 'username:\"%s\" pack:\"%s\"' % (pack_obj.user.username, pack_obj.name)
    #filter_query = 'pack:\"%s\"' % (pack_obj.name,)
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
