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
#     Bram de Jong
#
import json
import logging
import urllib.parse

from django.conf import settings
from django.core.cache import cache

from utils.search import SearchEngineException

search_logger = logging.getLogger("search")


class SolrQuery:
    """A wrapper around a lot of Solr query functionality.
    """

    def __init__(self):
        """Creates a SolrQuery object
        """
        # some default parameters
        self.params = {
            'wt': 'json',
            'indent': 'true',
            'debugQuery': 'true' if settings.DEBUG else 'false',
            'q.op': 'AND',
            'echoParams': 'explicit',
        }

    def set_query(self, query):
        self.params['q'] = query

    def set_dismax_query(self, query, query_fields=None, minimum_match=None, phrase_fields=None, phrase_slop=None,
                         query_phrase_slop=None, tie_breaker=None, boost_query=None, boost_functions=None):
        """Created a dismax query: http://wiki.apache.org/solr/DisMaxRequestHandler
        The DisMaxRequestHandler is designed to process simple user entered phrases (without heavy syntax) and search for the individual words
        across several fields using different weighting (boosts) based on the significance of each field. Additional options let you influence
        the score based on rules specific to each use case (independent of user input)

        query_fields: List of fields and the "boosts" to associate with each of them when building DisjunctionMaxQueries from the user's query.
                        should be a list of fields: ["tag", "description", "username"]
                        with optional boosts:  with boosts [("tag", 2), "description", ("username", 3)]
        minimum_match: see docs...
        phrase_fields: after the query, find (in these fields) fields that have all terms close together and boost them
        phrase_slop: amount of slop on phrase queries built for "pf" fields (affects boosting).
        query_phrase_slop: Amount of slop on phrase queries explicitly included in the user's query string (in qf fields; affects matching).
        tie_breaker: see docs...
        boost_query: see docs...
        boost_functions: see docs...
        """
        self.params['q'] = query
        self.params['defType'] = 'dismax'
        self.params['q.alt'] = '*:*'
        if query_fields:
            qf = []
            for f in query_fields:
                if isinstance(f, tuple):
                    qf.append("^".join(map(str, f)))
                else:
                    qf.append(f)

            self.params['qf'] = " ".join(qf)
        else:
            self.params['qf'] = None
        self.params['mm'] = minimum_match
        self.params['pf'] = " ".join(phrase_fields) if phrase_fields else phrase_fields
        self.params['ps'] = phrase_slop or '100'
        self.params['qs'] = query_phrase_slop
        self.params['tie'] = tie_breaker or '0.01'
        self.params['bq'] = boost_query
        self.params['bf'] = boost_functions

    def set_query_options(self, start=None, rows=None, sort=None, filter_query=None, field_list=None):
        """Set the options for the query.
        start: row where to start
        rows: row where to end
        sort: ['field1 desc', 'field2', 'field3 desc']
        filter_query: filter the returned results by this query
        field_list: ['field1', 'field2', ...] or ['*'] these fields will be returned, default: *
        """
        self.params['sort'] = ",".join(sort) if sort else sort
        self.params['start'] = start
        self.params['rows'] = rows
        self.params['fq'] = filter_query
        self.params['fl'] = ",".join(field_list) if field_list else field_list

    def add_facet_fields(self, *args):
        """Adds facet fields
        """
        self.params['facet'] = True
        try:
            self.params['facet.field'].extend(args)
        except KeyError:
            self.params['facet.field'] = list(args)

    def set_facet_query(self, query):
        """Set additional query for faceting
        """
        self.params['facet.query'] = query

    # set global faceting options for regular fields
    def set_facet_options_default(self, limit=None, offset=None, prefix=None, sort=None, mincount=None,
                                  count_missing=None, enum_cache_mindf=None):
        """Set default facet options: these will be applied to all facets, but overridden by particular options (see set_facet_options())
        prefix: return only facets with this prefix
        sort: sort facets, True or False
        limit: nr of facets to return
        offset: start from this row
        mincount: minimum hits a facet needs to be listed
        count_missing: count items that don't have this facet, True or False
        enum_cache_mindf: when faceting on a field with a very large number of terms, and you wish to decrease memory usage, try a low value of 25 to 50 first
        """
        self.params['facet.limit'] = limit
        self.params['facet.offset'] = offset
        self.params['facet.prefix'] = prefix
        self.params['facet.sort'] = sort
        self.params['facet.mincount'] = mincount
        self.params['facet.missing'] = count_missing
        self.params['facet.enum.cache.minDf'] = enum_cache_mindf

    # set faceting options for one particular field
    def set_facet_options(self, field, prefix=None, sort=None, limit=None, offset=None, mincount=None,
                          count_missing=None):
        """Set facet options for one particular field... see set_facet_options_default() for parameter explanation
        """
        try:
            if field not in self.params['facet.field']:
                raise SearchEngineException("setting facet options for field that doesn't exist")
        except KeyError:
            raise SearchEngineException("you haven't defined any facet fields yet")

        self.params[f'f.{field}.facet.limit'] = limit
        self.params[f'f.{field}.facet.offset'] = offset
        self.params[f'f.{field}.facet.prefix'] = prefix
        self.params[f'f.{field}.facet.sort'] = sort
        self.params[f'f.{field}.facet.mincount'] = mincount
        self.params[f'f.{field}.facet.missing'] = count_missing

    def set_facet_json_api(self, json_facets):
        # See https://solr.apache.org/guide/solr/9_0/query-guide/json-facet-api.html
        self.params['json.facet'] = json.dumps(json_facets)

    def add_date_facet_fields(self, *args):
        """Add date facet fields
        """
        self.params['facet'] = True
        try:
            self.params['facet.date'].extend(args)
        except KeyError:
            self.params['facet.date'] = list(args)

    def set_date_facet_options_default(self, start=None, end=None, gap=None, hardend=None, count_other=None):
        """Set default date facet options: these will be applied to all date facets, but overridden by particular options (see set_date_facet_options())
            start: date start in DateMathParser syntax
            end: date end in DateMathParser syntax
            gap: size of slices of date range
            hardend: True: if gap doesn't divide range make last slice smaller. False: go out of bounds with last slice
            count_other: A tuple of other dates to count: before, after, between, none, all
        """
        self.params['facet.date.start'] = start
        self.params['facet.date.end'] = start
        self.params['facet.date.gap'] = gap
        self.params['facet.date.hardend'] = hardend
        self.params['facet.date.other'] = count_other

    def set_date_facet_options(self, field, start=None, end=None, gap=None, hardened=None, count_other=None):
        """Set date facet options for one particular field... see set_date_facet_options_default() for parameter explanation
        """
        try:
            if field not in self.params['facet.date']:
                raise SearchEngineException("setting date facet options for field that doesn't exist")
        except KeyError:
            raise SearchEngineException("you haven't defined any date facet fields yet")

        self.params[f'f.{field}.date.start'] = start
        self.params[f'f.{field}.date.end'] = start
        self.params[f'f.{field}.date.gap'] = gap
        self.params[f'f.{field}.date.hardend'] = hardened
        self.params[f'f.{field}.date.other'] = count_other

    def set_highlighting_options_default(self, field_list=None, snippets=None, fragment_size=None,
                                         merge_contiguous=None, require_field_match=None, max_analyzed_chars=None,
                                         alternate_field=None, max_alternate_field_length=None, pre=None, post=None,
                                         fragmenter=None, use_phrase_highlighter=None, regex_slop=None,
                                         regex_pattern=None, regex_max_analyzed_chars=None):
        """Set default highlighting options: these will be applied to all highlighting, but overridden by particular options (see set_highlighting_options())
        field_list: list of fields to highlight space separated
        snippets: number of snippets to generate
        fragment_size: snippet size, default: 1
        merge_contiguous: merge continuous snippets into one, True or False
        require_field_match: If True, then a field will only be highlighted if the query matched in this particular field
        max_analyzed_chars: How many characters into a document to look for suitable snippets
        alternate_field: if no match is found, use this field as summary
        max_alternate_field_length: size to clip the alternate field to
        pre: what to put before the snippet (like <strong>)
        post: what to put after the snippet (like </strong>)
        fragmenter: specify a text snippet generator for highlighted text.
        use_phrase_highlighter: use SpanScorer to highlight phrase terms only when they appear within the query phrase in the document.
        regex_slop: factor by which the regex fragmenter can stray from the ideal fragment size (given by hl.fragsize) to accommodate the regular expression
        regex_pattern: the regular expression for fragmenting.
        regex_max_analyzed_chars: only analyze this many characters from a field when using the regex fragmenter
        """
        self.params['hl'] = True
        self.params['hl.fl'] = ",".join(field_list) if field_list else field_list
        self.params['hl.fl.snippets'] = snippets
        self.params['hl.fragsize'] = fragment_size
        self.params['hl.mergeContiguous'] = merge_contiguous
        self.params['hl.requireFieldMatch'] = require_field_match
        self.params['hl.maxAnalyzedChars'] = max_analyzed_chars
        self.params['hl.alternateField'] = alternate_field
        self.params['hl.maxAlternateFieldLength'] = max_alternate_field_length
        # self.params['hl.formatter'] = # only valid one is "simple" right now
        self.params['hl.simple.pre'] = pre
        self.params['hl.simple.post'] = post
        self.params['hl.fragmenter'] = fragmenter
        self.params['hl.usePhraseHighlighter'] = use_phrase_highlighter
        self.params['hl.regex.slop'] = regex_slop
        self.params['hl.regex.pattern'] = regex_pattern
        self.params['hl.regex.maxAnalyzedChars'] = regex_max_analyzed_chars

    def set_highlighting_options(self, field, snippets=None, fragment_size=None, merge_contiguous=None,
                                 alternate_field=None, pre=None, post=None):
        """Set highlighting options for one particular field... see set_highlighting_options_default() for parameter explanation
        """
        try:
            if field not in self.params['hl.fl']:
                raise SearchEngineException("setting highlighting options for field that doesn't exist")
        except KeyError:
            raise SearchEngineException("you haven't defined any highlighting fields yet")

        self.params[f'f.{field}.hl.fl.snippets'] = snippets
        self.params[f'f.{field}.hl.fragsize'] = fragment_size
        self.params[f'f.{field}.hl.mergeContiguous'] = merge_contiguous
        self.params[f'f.{field}.hl.alternateField'] = alternate_field
        self.params[f'f.{field}.hl.simple.pre'] = pre
        self.params[f'f.{field}.hl.simple.post'] = post

    def __str__(self):
        return urllib.parse.urlencode(self.params, doseq=True)

    def set_group_field(self, group_field=None):
        self.params['group.field'] = group_field

    def set_group_options(self, group_func=None, group_query=None, group_start=0, group_limit=1,
                          group_offset=0, group_sort=None, group_sort_ingroup=None, group_format='grouped',
                          group_main=False, group_num_groups=True, group_cache_percent=0, group_truncate=False):
        self.params['group'] = True
        self.params['group.func'] = group_func
        self.params['group.query'] = group_query
        self.params['group.start'] = group_start
        self.params['group.limit'] = group_limit
        self.params['group.offset'] = group_offset
        self.params['group.sort'] = group_sort
        self.params['group.sort.ingroup'] = group_sort_ingroup
        self.params['group.format'] = group_format
        self.params['group.main'] = group_main
        self.params['group.ngroups'] = group_num_groups
        self.params['group.truncate'] = group_truncate
        self.params['group.cache.percent'] = group_cache_percent

    def as_kwargs(self):
        """Return params in a way that can be passed to pysolr commands as kwargs"""
        params = {k: v for k, v in self.params.items() if v is not None}
        for k, v in params.items():
            if isinstance(v, bool):
                params[k] = json.dumps(v)
        return params


def make_solr_query_url(solr_query_params, debug=False):
    if debug:
        solr_query_params['debugQuery'] = 'true'
    query_params = urllib.parse.urlencode(solr_query_params, doseq=True, safe=':/?&",\{\}*^')
    return f"{settings.SEARCH_LOG_SLOW_QUERIES_QUERY_BASE_URL}?{query_params}"


class SolrResponseInterpreter:
    def __init__(self, response, next_page_query=None):

        if "grouped" in response and "expanded" in response:
            raise SearchEngineException("Response contains both grouped and expanded results, this is not supported")
        
        if "grouped" in response:
            grouping_field = list(response["grouped"].keys())[0]     
            self.docs = [{
                'id': group['doclist']['docs'][0]['id'],
                'score': group['doclist']['docs'][0].get('score', 0),
                'n_more_in_group': group['doclist']['numFound'] - 1,
                'group_docs': group['doclist']['docs'],
                'group_name': group['groupValue']
            } for group in response["grouped"][grouping_field]["groups"] if group['groupValue'] is not None]
            self.start = int(response["responseHeader"]["params"]["start"])
            self.num_rows = len(self.docs)
            self.num_found = response["grouped"][grouping_field]["ngroups"]
            self.non_grouped_number_of_results = response["grouped"][grouping_field]["matches"]
        elif "expanded" in response:
            collapse_field = 'pack_grouping_child' if 'pack_grouping_child' in response['responseHeader']['params']['fl'] else 'pack_grouping'
            self.docs = []
            for doc in response["response"]["docs"]:
                group_name = doc[collapse_field] if collapse_field in doc else ''
                group_docs = response['expanded'][doc[collapse_field]]['docs'] if collapse_field in doc and doc[collapse_field] in response['expanded'] else []
                group_docs = [doc] + group_docs  # Add the original document to the group docs list
                n_more_in_group = response['expanded'][doc[collapse_field]]['numFound'] if collapse_field in doc and doc[collapse_field] in response['expanded'] else 0
                self.docs.append({
                    'id': doc['id'],
                    'score': doc['score'],
                    'n_more_in_group': n_more_in_group,
                    'group_docs': group_docs,
                    'group_name': group_name
                })
            self.start = int(response["response"]["start"])
            self.num_rows = len(self.docs)
            self.num_found = response["response"]["numFound"]  # This corresponds to the total number of groups (including sounds without group being counted as one group because of nullPolicy=expand)
            self.non_grouped_number_of_results = -1. # When using the collapse and expand query parser, we don't know the number of uncollapsed results, this will be obtained later making a second query
        else:
            self.docs = response["response"]["docs"]
            self.start = int(response["response"]["start"])
            self.num_rows = len(self.docs)
            self.num_found = response["response"]["numFound"]
            self.non_grouped_number_of_results = 0

        self.q_time = response["responseHeader"]["QTime"]

        self.facets = {}
        if 'facet_counts' in response:
            # "old" Solr faceting format
            # Facets are given in a list: [facet, number, facet, number, None, number] where the last one
            # is the missing field count. Converting all of them to a dict for easier usage:
            # {facet:number, facet:number, ..., None:number}
            self.facets = response["facet_counts"]["facet_fields"]
            for facet, fields in list(self.facets.items()):
                self.facets[facet] = [(fields[index], fields[index + 1]) for index in range(0, len(fields), 2)]
        if 'facets' in response:
            # New faceting format, https://solr.apache.org/guide/solr/9_2/query-guide/json-facet-api.html
            for facet_name, data in response['facets'].items():
                if facet_name != 'count':
                    self.facets[facet_name] = [(str(b['val']), b['count']) for b in data['buckets']]

        try:
            self.highlighting = response["highlighting"]
        except KeyError:
            self.highlighting = {}

        if settings.DEBUG or (settings.SEARCH_LOG_SLOW_QUERIES_MS_THRESHOLD > -1 and self.q_time > settings.SEARCH_LOG_SLOW_QUERIES_MS_THRESHOLD):
            solr_query_url = make_solr_query_url(response['responseHeader']['params'], debug=True) 
            
            # If query is slow, log the SOLR parameters so we can debug it later (this works in production environment as well)
            if settings.SEARCH_LOG_SLOW_QUERIES_MS_THRESHOLD > -1 and self.q_time > settings.SEARCH_LOG_SLOW_QUERIES_MS_THRESHOLD:
                search_logger.info('SOLR slow query detected (%s)' % json.dumps({
                    'q_time': self.q_time,
                    'num_results': self.num_found, 
                    'url': solr_query_url
                }))
        
            if settings.DEBUG: 
                # If in debug mode, store query stats in cache so they can be loaded by the SOLR debug panel
                query_info = {
                    'num_results': self.num_found,
                    'time': self.q_time,
                    'query_solr_url': solr_query_url,
                    'query_solr_response': response,
                }
                info_for_panel = cache.get("solr_debug_panel_query_info")
                if info_for_panel is None:
                    info_for_panel = []
                info_for_panel.append(query_info)
                cache.set("solr_debug_panel_query_info", info_for_panel, 60 * 60)

