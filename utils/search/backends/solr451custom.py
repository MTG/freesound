# -*- coding: utf-8 -*-

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
import itertools
import math
import random
import re
import urllib
from datetime import date, datetime
from socket import error
from time import strptime
from xml.etree import cElementTree as ET

import cjson
import httplib
import urlparse

from django.conf import settings

from forum.models import Post
from sounds.models import Sound
from utils.text import remove_control_chars
from utils.search import SearchEngineBase, SearchEngineException, SearchResults

SOLR_SOUNDS_URL = settings.SOLR_SOUNDS_URL
SOLR_FORUM_URL = settings.SOLR_FORUM_URL

# Mapping from db sound field names to solr sound field names
FIELD_NAMES_MAP = {
    settings.SEARCH_SOUNDS_FIELD_ID: 'id',
    settings.SEARCH_SOUNDS_FIELD_NAME: 'original_filename',
    settings.SEARCH_SOUNDS_FIELD_TAGS: 'tag',
    settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 'description',
    settings.SEARCH_SOUNDS_FIELD_USER_NAME: 'username',
    settings.SEARCH_SOUNDS_FIELD_PACK_NAME: 'pack_tokenized',
    settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING: 'grouping_pack',
    settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: 'samplerate',
    settings.SEARCH_SOUNDS_FIELD_BITRATE: 'bitrate',
    settings.SEARCH_SOUNDS_FIELD_BITDEPTH: 'bitdepth',
    settings.SEARCH_SOUNDS_FIELD_TYPE: 'type',
    settings.SEARCH_SOUNDS_FIELD_CHANNELS: 'channels',
    settings.SEARCH_SOUNDS_FIELD_LICENSE_NAME: 'license'
}

# Map "web" sorting options to solr sorting options
SORT_OPTIONS_MAP = {
    settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC: "score desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST: "duration desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST: "duration asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST: "created desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST: "created asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST: "num_downloads desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST: "num_downloads asc",
    settings.SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST: "avg_rating desc",
    settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST: "avg_rating asc"
}

# Map of suffixes used for each type of dynamic fields defined in our Solr schema
# The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer),
# '*_s' (for string) and '*_ls' (for lists of strings)
SOLR_DYNAMIC_FIELDS_SUFFIX_MAP = {
    float: '_d',
    int: '_i',
    bool: '_b',
    str: '_s',
    unicode: '_s',
    list: '_ls',
}

SOLR_SOUND_FACET_DEFAULT_OPTIONS = {
    'limit': 5,
    'sort': True,
    'mincount': 1,
    'count_missing': False
}

SOLR_PACK_GROUPING_OPTIONS = {
    'field': settings.SEARCH_SOUNDS_FIELD_PACK_GROUPING,
    'limit': 1,
}


class Multidict(dict):
    """A dictionary that represents a query string. If values in the dics are tuples, they are expanded.
    None values are skipped and all values are utf-encoded. We need this because in solr, we can have multiple
    fields with the same value, like facet.field

    >>> [ (key, value) for (key,value) in Multidict({"a": 1, "b": (2,3,4), "c":None, "d":False}).items() ]
    [('a', 1), ('b', 2), ('b', 3), ('b', 4), ('d', 'false')]
    """

    def items(self):
        # generator that retuns all items
        def all_items():
            for (key, value) in dict.items(self):
                if isinstance(value, tuple) or isinstance(value, list):
                    for v in value:
                        yield key, v
                else:
                    yield key, value

        # generator that filters all items: drop (key, value) pairs with value=None and convert bools to lower case strings
        for (key, value) in itertools.ifilter(lambda (key, value): value != None and value != "", all_items()):
            if isinstance(value, bool):
                value = unicode(value).lower()
            else:
                value = unicode(value).encode('utf-8')

            yield (key, value)


def convert_sound_to_search_engine_document(sound):
    document = {}

    # Basic sound fields
    keep_fields = ['username', 'created', 'is_explicit', 'is_remix', 'num_ratings', 'channels', 'md5',
                   'was_remixed', 'original_filename', 'duration', 'type', 'id', 'num_downloads', 'filesize']
    for key in keep_fields:
        document[key] = getattr(sound, key)
    document["original_filename"] = remove_control_chars(getattr(sound, "original_filename"))
    document["description"] = remove_control_chars(getattr(sound, "description"))
    document["tag"] = getattr(sound, "tag_array")
    document["license"] = getattr(sound, "license_name")
    if document["num_ratings"] >= settings.MIN_NUMBER_RATINGS:
        document["avg_rating"] = getattr(sound, "avg_rating")
    else:
        document["avg_rating"] = 0

    if getattr(sound, "pack_id"):
        document["pack"] = remove_control_chars(getattr(sound, "pack_name"))
        document["grouping_pack"] = str(getattr(sound, "pack_id")) + "_" + remove_control_chars(
            getattr(sound, "pack_name"))
    else:
        document["grouping_pack"] = str(getattr(sound, "id"))

    document["is_geotagged"] = False
    if getattr(sound, "geotag_id"):
        document["is_geotagged"] = True
        if not math.isnan(getattr(sound, "geotag_lon")) and not math.isnan(getattr(sound, "geotag_lat")):
            document["geotag"] = str(getattr(sound, "geotag_lon")) + " " + str(getattr(sound, "geotag_lat"))

    document["bitdepth"] = getattr(sound, "bitdepth") if getattr(sound, "bitdepth") else 0
    document["bitrate"] = getattr(sound, "bitrate") if getattr(sound, "bitrate") else 0
    document["samplerate"] = int(getattr(sound, "samplerate")) if getattr(sound, "samplerate") else 0

    document["comment"] = [remove_control_chars(comment_text) for comment_text in getattr(sound, "comments_array")]
    document["comments"] = getattr(sound, "num_comments")
    locations = sound.locations()
    document["waveform_path_m"] = locations["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = locations["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = locations["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = locations["display"]["spectral"]["L"]["path"]
    document["preview_path"] = locations["preview"]["LQ"]["mp3"]["path"]

    # Analyzer's output
    for analyzer_name, analyzer_info in settings.ANALYZERS_CONFIGURATION.items():
        if 'query_select_name' in analyzer_info:
            query_select_name = analyzer_info['query_select_name']
            analysis_data = getattr(sound, query_select_name, None)
            if analysis_data is not None:
                # If analysis is present, index all existing analysis fields using SOLR dynamic fields depending on
                # the value type (see SOLR_DYNAMIC_FIELDS_SUFFIX_MAP) so solr knows how to treat when filtering, etc.
                for key, value in analysis_data.items():
                    if type(value) == list:
                        # Make sure that the list is formed by strings
                        value = ['{}'.format(item) for item in value]
                    suffix = SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.get(type(value), None)
                    if suffix:
                        document['{0}{1}'.format(key, suffix)] = value
    return document


def convert_post_to_search_engine_document(post):
    document = {
        "id": post.id,
        "thread_id": post.thread.id,
        "thread_title": remove_control_chars(post.thread.title),
        "thread_author": post.thread.author,
        "thread_created": post.thread.created,

        "forum_name": post.thread.forum.name,
        "forum_name_slug": post.thread.forum.name_slug,

        "post_author": post.author,
        "post_created": post.created,
        "post_body": remove_control_chars(post.body),

        "num_posts": post.thread.num_posts,
        "has_posts": False if post.thread.num_posts == 0 else True
    }
    return document


def search_process_filter(query_filter, only_sounds_within_ids=False, only_sounds_with_pack=False):
    """Process the filter to make a number of adjustments

        1) Add type suffix to human-readable audio analyzer descriptor names (needed for dynamic solr field names).
        2) If only sounds with pack should be returned, add such a filter.
        3) Add filter for sound IDs if only_sounds_within_ids is passed.

    Step 1) is used for the dynamic field names used in Solr (e.g. ac_tonality -> ac_tonality_s, ac_tempo ->
    ac_tempo_i). The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float),
    '*_i' (for integer) and '*_s' (for string). At indexing time, we append these suffixes to the analyzer
    descriptor names that need to be indexed so Solr can treat the types properly. Now we automatically append the
    suffices to the filter names so users do not need to deal with that and Solr understands recognizes the field name.

    Args:
        query_filter (str): query filter string.
        only_sounds_with_pack (bool, optional): whether to only include sounds that belong to a pack
        only_sounds_within_ids (List[int], optional): restrict search results to sounds with these IDs

    Returns:
        str: processed filter query string.
    """
    # Add type suffix to human-readable audio analyzer descriptor names which is needed for solr dynamic fields
    for analyzer, analyzer_data in settings.ANALYZERS_CONFIGURATION.items():
        if 'descriptors_map' in analyzer_data:
            descriptors_map = settings.ANALYZERS_CONFIGURATION[analyzer]['descriptors_map']
            for _, db_descriptor_key, descriptor_type in descriptors_map:
                query_filter = query_filter.replace('{0}:'.format(db_descriptor_key),
                                                    '{0}{1}:'.format(db_descriptor_key,
                                                                     SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[descriptor_type]))

    # If we only want sounds with packs and there is no pack filter, add one
    if only_sounds_with_pack and not 'pack:' in query_filter:
        query_filter += ' pack:*'

    # When calculating results form clustering, the "only_sounds_within_ids" argument is passed and we filter
    # our query to the sounds in that list of IDs.
    if only_sounds_within_ids:
        sounds_within_ids_filter = ' OR '.join(['id:{}'.format(sound_id) for sound_id in only_sounds_within_ids])
        if query_filter:
            query_filter += ' AND ({})'.format(sounds_within_ids_filter)
        else:
            query_filter = '({})'.format(sounds_within_ids_filter)

    return query_filter


def search_process_sort(sort):
    """Translates sorting criteria to solr sort criteria and add extra criteria if sorting by ratings.

    If order by rating, when rating is the same sort also by number of ratings.

    Args:
        sort (str): sorting criteria as defined in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB.

    Returns:
        List[str]: list containing the sorting field names list for the search engine.
    """
    if sort in [sort_web_name for sort_web_name, sort_field_name in SORT_OPTIONS_MAP.items()]:
        if sort == "avg_rating desc":
            sort = [SORT_OPTIONS_MAP[sort], "num_ratings desc"]
        elif sort == "avg_rating asc":
            sort = [SORT_OPTIONS_MAP[sort], "num_ratings asc"]
        else:
            sort = [SORT_OPTIONS_MAP[sort]]
    else:
        sort = [SORT_OPTIONS_MAP[settings.SEARCH_SOUNDS_SORT_DEFAULT]]
    return sort


class SolrQuery(object):
    """A wrapper around a lot of Solr query funcionality.
    """

    def __init__(self, query_type=None, writer_type="json", indent=None, debug_query=None):
        """Creates a SolrQuery object
        query_type: Which handler to use when replying, default: default, dismax
        writer_type: Available types are: SolJSON, SolPHP, SolPython, SolRuby, XMLResponseFormat, XsltResponseWriter
        indent: format output with indentation or not
        debug_query: if 1 output debug infomation
        """
        # some default parameters
        self.params = {
            'qt': query_type,
            'wt': writer_type,
            'indent': indent,
            'debugQuery': debug_query
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
        self.params['qt'] = "dismax"
        self.params['q'] = query
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
        self.params['ps'] = phrase_slop
        self.params['qs'] = query_phrase_slop
        self.params['tie'] = tie_breaker
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
        prefix: retun only facets with this prefix
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
                raise SearchEngineException, "setting facet options for field that doesn't exist"
        except KeyError:
            raise SearchEngineException, "you haven't defined any facet fields yet"

        self.params['f.%s.facet.limit' % field] = limit
        self.params['f.%s.facet.offset' % field] = offset
        self.params['f.%s.facet.prefix' % field] = prefix
        self.params['f.%s.facet.sort' % field] = sort
        self.params['f.%s.facet.mincount' % field] = mincount
        self.params['f.%s.facet.missing' % field] = count_missing

    def add_date_facet_fields(self, *args):
        """Add date facet fields
        """
        self.params['facet'] = True
        try:
            self.params['facet.date'].extend(args)
        except KeyError:
            self.params['facet.date'] = list(args)

    def set_date_facet_options_default(self, start=None, end=None, gap=None, hardened=None, count_other=None):
        """Set default date facet options: these will be applied to all date facets, but overridden by particular options (see set_date_facet_options())
            start: date start in DateMathParser syntax
            end: date end in DateMathParser syntax
            gap: size of slices of date range
            hardend: True: if gap doesn't devide range make last slice smaller. False: go out of bounds with last slice
            count_other: A tuple of other dates to count: before, after, between, none, all
        """
        self.params['facet.date.start'] = start
        self.params['facet.date.end'] = start
        self.params['facet.date.gap'] = gap
        self.params['facet.date.hardend'] = hardened
        self.params['facet.date.other'] = count_other

    def set_date_facet_options(self, field, start=None, end=None, gap=None, hardened=None, count_other=None):
        """Set date facet options for one particular field... see set_date_facet_options_default() for parameter explanation
        """
        try:
            if field not in self.params['facet.date']:
                raise SearchEngineException, "setting date facet options for field that doesn't exist"
        except KeyError:
            raise SearchEngineException, "you haven't defined any date facet fields yet"

        self.params['f.%s.date.start' % field] = start
        self.params['f.%s.date.end' % field] = start
        self.params['f.%s.date.gap' % field] = gap
        self.params['f.%s.date.hardend' % field] = hardened
        self.params['f.%s.date.other' % field] = count_other

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
        regex_slop: factor by which the regex fragmenter can stray from the ideal fragment size (given by hl.fragsize) to accomodate the regular expression
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
                raise SearchEngineException, "setting highlighting options for field that doesn't exist"
        except KeyError:
            raise SearchEngineException, "you haven't defined any highlighting fields yet"

        self.params['f.%s.hl.fl.snippets' % field] = snippets
        self.params['f.%s.hl.fragsize' % field] = fragment_size
        self.params['f.%s.hl.mergeContiguous' % field] = merge_contiguous
        self.params['f.%s.hl.alternateField' % field] = alternate_field
        self.params['f.%s.hl.simple.pre' % field] = pre
        self.params['f.%s.hl.simple.post' % field] = post

    def __unicode__(self):
        return urllib.urlencode(Multidict(self.params))

    def set_group_field(self, group_field=None):
        self.params['group.field'] = group_field

    def set_group_options(self, group_func=None, group_query=None, group_rows=10, group_start=0, group_limit=1,
                          group_offset=0, group_sort=None, group_sort_ingroup=None, group_format='grouped',
                          group_main=False, group_num_groups=True, group_cache_percent=0, group_truncate=False):
        self.params['group'] = True
        self.params['group.func'] = group_func
        self.params['group.query'] = group_query
        self.params['group.rows'] = group_rows
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


class BaseSolrAddEncoder(object):
    """A Solr Add encoder has one method, called encode. This method will be called on whatever is
    passed to the Solr add() method. It should return an XML compatible with the installed Solr schema.

    >>> encoder = BaseSolrAddEncoder()
    >>> encoder.encode([{"id": 5, "name": "guido", "tag":["python", "coder"], "status":"bdfl"}])
    '<add><doc><field name="status">bdfl</field><field name="tag">python</field><field name="tag">coder</field><field name="id">5</field><field name="name">guido</field></doc></add>'
    """

    def encode(self, docs):
        """Encodes a document as an XML tree. this particular one takes a dictionary and
        translates the key value pairs to <field name="key">value<f/field>
        """
        message = ET.Element('add')

        def add_basic_type(element, name, value):
            """Converts python values to a form suitable for insertion into the xml
            we send to solr and adds it to the doc XML.
            """
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            elif isinstance(value, date):
                value = value.strftime('%Y-%m-%dT00:00:00.000Z')
            elif isinstance(value, bool):
                if value:
                    value = 'true'
                else:
                    value = 'false'
            else:
                value = unicode(value)

            field = ET.Element('field', name=name)
            field.text = value
            element.append(field)

        for doc in docs:
            d = ET.Element('doc')
            for key, value in doc.items():
                # handle lists, tuples, and other iterabes
                if isinstance(value, (list, tuple)):
                    for v in value:
                        add_basic_type(d, key, v)
                # handle strings and unicode
                else:
                    add_basic_type(d, key, value)
            message.append(d)

        return ET.tostring(message, "utf-8")


class SolrResponseDecoderException(Exception):
    pass


class BaseSolrResponseDecoder(object):
    """The BaseSolrResponseDecoder takes the Response object from urllib2 and decodes it"""


class SolrJsonResponseDecoder(BaseSolrResponseDecoder):

    def __init__(self):
        # matches returned dates in JSON strings
        self.date_match = re.compile("-?\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.?\d*[a-zA-Z]*")

    def decode(self, response_object):
        # return self._decode_dates(json.load(response_object))
        return self._decode_dates(cjson.decode(unicode(response_object.read(), 'utf-8')))  # @UndefinedVariable

    def _decode_dates(self, d):
        """Recursively decode date strings to datetime objects.
        """
        if isinstance(d, dict):
            for key, value in d.items():
                d[key] = self._decode_dates(value)
        elif isinstance(d, list):
            for index, value in enumerate(d):
                d[index] = self._decode_dates(value)
        elif isinstance(d, basestring):
            if self.date_match.match(d):
                try:
                    d = datetime(*strptime(d[0:19], "%Y-%m-%dT%H:%M:%S")[0:6])
                except:
                    raise SolrResponseDecoderException, u"Response object has unknown date format: %s" % d
        return d


class Solr(object):
    def __init__(self, url, verbose=False, persistent=False, encoder=BaseSolrAddEncoder(),
                 decoder=SolrJsonResponseDecoder()):
        url_split = urlparse.urlparse(url)

        self.host = url_split.hostname
        self.port = url_split.port
        self.path = url_split.path.rstrip('/')

        self.decoder = decoder
        self.encoder = encoder
        self.verbose = verbose

        self.persistent = persistent

        if self.persistent:
            self.conn = httplib.HTTPConnection(self.host, self.port)

    def _request(self, query_string="", message=""):
        if query_string != "":
            path = '%s/select/?%s' % (self.path, query_string)
        else:
            path = '%s/update' % self.path

        if self.verbose:
            print "Connecting to Solr server: %s:%s" % (self.host, self.port)
            print "\tPath:", path
            print "\tSending data:", message

        if self.persistent:
            conn = self.conn
        else:
            conn = httplib.HTTPConnection(self.host, self.port)

        if query_string:
            conn.request('GET', path)
        elif message:
            conn.request('POST', path, message, {'Content-type': 'text/xml'})

        response = conn.getresponse()

        if response.status != 200:
            raise SearchEngineException, response.reason

        return response

    def select(self, query_string, raw=False):
        if raw:
            return unicode(self._request(query_string=query_string).read())
        else:
            return self.decoder.decode(self._request(query_string=query_string))

    def add(self, docs):
        encoded_docs = self.encoder.encode(docs)
        try:
            self._request(message=encoded_docs)
        except error as e:
            raise SearchEngineException(e)

    def delete_by_id(self, id):
        try:
            self._request(message=u'<delete><id>%s</id></delete>' % unicode(id))
        except error as e:
            raise SearchEngineException(e)

    def delete_by_query(self, query):
        try:
            self._request(message=u'<delete><query>%s</query></delete>' % unicode(query))
        except error as e:
            raise SearchEngineException(e)

    def commit(self, wait_searcher=True):
        message = ET.Element('commit')
        message.set("waitSearcher", str(wait_searcher).lower())
        self._request(message=ET.tostring(message, "utf-8"))

    def optimize(self, wait_flush=True, wait_searcher=True):
        message = ET.Element('optimize')
        message.set("waitFlush", str(wait_flush).lower())
        message.set("waitSearcher", str(wait_searcher).lower())
        self._request(message=ET.tostring(message, "utf-8"))


class SolrResponseInterpreter(object):
    def __init__(self, response):
        if "grouped" in response:
            if "thread_title_grouped" in response["grouped"].keys():
                grouping_field = "thread_title_grouped"
            elif "grouping_pack" in response["grouped"].keys():
                grouping_field = "grouping_pack"

            self.docs = [{
                'id': group['doclist']['docs'][0]['id'],
                'n_more_in_group': group['doclist']['numFound'] - 1,
                'group_docs': group['doclist']['docs'],
                'group_name': group['groupValue']
            } for group in response["grouped"][grouping_field]["groups"] if group['groupValue'] is not None]
            self.start = int(response["responseHeader"]["params"]["start"])
            self.num_rows = len(self.docs)
            self.num_found = response["grouped"][grouping_field]["ngroups"]
            self.non_grouped_number_of_results = response["grouped"][grouping_field]["matches"]
        else:
            self.docs = response["response"]["docs"]
            self.start = int(response["response"]["start"])
            self.num_rows = len(self.docs)
            self.num_found = response["response"]["numFound"]
            self.non_grouped_number_of_results = -1

        self.q_time = response["responseHeader"]["QTime"]
        try:
            self.facets = response["facet_counts"]["facet_fields"]
        except KeyError:
            self.facets = {}

        """Facets are given in a list: [facet, number, facet, number, None, number] where the last one
        is the missing field count. Converting all of them to a dict for easier usage:
        {facet:number, facet:number, ..., None:number}
        """
        for facet, fields in self.facets.items():
            self.facets[facet] = [(fields[index], fields[index + 1]) for index in range(0, len(fields), 2)]

        try:
            self.highlighting = response["highlighting"]
        except KeyError:
            self.highlighting = {}


class Solr451CustomSearchEngine(SearchEngineBase):
    sounds_index = None
    forum_index = None

    def get_sounds_index(self):
        if self.sounds_index is None:
            self.sounds_index = Solr(SOLR_SOUNDS_URL,
                                     verbose=False,
                                     persistent=False,
                                     encoder=BaseSolrAddEncoder(),
                                     decoder=SolrJsonResponseDecoder())
        return self.sounds_index

    def get_forum_index(self):
        if self.forum_index is None:
            self.forum_index = Solr(SOLR_FORUM_URL,
                                    verbose=False,
                                    persistent=False,
                                    encoder=BaseSolrAddEncoder(),
                                    decoder=SolrJsonResponseDecoder())
        return self.forum_index

    # Sound methods

    def add_sounds_to_index(self, sound_objects):
        documents = [convert_sound_to_search_engine_document(s) for s in sound_objects]
        self.get_sounds_index().add(documents)
        if settings.DEBUG:
            # Sending the commit message generates server errors in production, we should investigate that... it could
            # be related with a different version of solr running locally. In any case, this line was added only
            # recently together with the refactoring of search engine backends so that we could force committing while
            # testing, but it is not needed in production
            self.get_sounds_index().commit()

    def remove_sounds_from_index(self, sound_objects_or_ids):
        for sound_object_or_id in sound_objects_or_ids:
            if type(sound_object_or_id) != Sound:
                sound_id = sound_object_or_id
            else:
                sound_id = sound_object_or_id.id
            self.get_sounds_index().delete_by_id(sound_id)
        if settings.DEBUG:
            # Sending the commit message generates server errors in production, we should investigate that... it could
            # be related with a different version of solr running locally. In any case, this line was added only
            # recently together with the refactoring of search engine backends so that we could force committing while
            # testing, but it is not needed in production
            self.get_sounds_index().commit()

    def sound_exists_in_index(self, sound_object_or_id):
        if type(sound_object_or_id) != Sound:
            sound_id = sound_object_or_id
        else:
            sound_id = sound_object_or_id.id
        response = self.search_sounds(query_filter='id:{}'.format(sound_id), offset=0, num_sounds=1)
        return response.num_found > 0

    def search_sounds(self, textual_query='', query_fields=None, query_filter='', offset=0, current_page=None,
                      num_sounds=settings.SOUNDS_PER_PAGE, sort=settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC,
                      group_by_pack=False, facets=None, only_sounds_with_pack=False, only_sounds_within_ids=False,
                      group_counts_as_one_in_facets=False):

        query = SolrQuery()

        # Process search fields: replace "db" field names by solr field names and set default weights if needed
        if query_fields is None:
            # If no fields provided, use the default
            query_fields = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS
        if type(query_fields) == list:
            query_fields = [FIELD_NAMES_MAP[field] for field in query_fields]
        elif type(query_fields) == dict:
            # Also remove fields with weight <= 0
            query_fields = [(FIELD_NAMES_MAP[field], weight) for field, weight in query_fields.items() if weight > 0]

        # Set main query options
        query.set_dismax_query(textual_query, query_fields=query_fields)

        # Process filter
        query_filter = search_process_filter(query_filter,
                                             only_sounds_within_ids=only_sounds_within_ids,
                                             only_sounds_with_pack=only_sounds_with_pack)

        # Set other query options
        if current_page is not None:
            offset = (current_page - 1) * num_sounds
        query.set_query_options(start=offset,
                                rows=num_sounds,
                                field_list=["id"],  # We only want the sound IDs of the results as we load data from DB
                                filter_query=query_filter,
                                sort=search_process_sort(sort))

        # Configure facets
        if facets is not None:
            facet_fields = [FIELD_NAMES_MAP[field_name] for field_name, _ in facets.items()]
            query.add_facet_fields(*facet_fields)
            query.set_facet_options_default(**SOLR_SOUND_FACET_DEFAULT_OPTIONS)
            for field_name, extra_options in facets.items():
                query.set_facet_options(FIELD_NAMES_MAP[field_name], **extra_options)

        # Configure grouping
        if group_by_pack:
            query.set_group_field(group_field="grouping_pack")
            query.set_group_options(
                group_func=None,
                group_query=None,
                group_rows=10,  # TODO: if limit is lower than rows and start=0, this should probably be equal to limit
                group_start=0,
                group_limit=1,  # This is the number of documents that will be returned for each group.
                group_offset=0,
                group_sort=None,
                group_sort_ingroup=None,
                group_format='grouped',
                group_main=False,
                group_num_groups=True,
                group_cache_percent=0,
                group_truncate=group_counts_as_one_in_facets)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter. This would not be strictly
        # needed because SearchResults and SolrResponseInterpreter are virtually the same, but we do it in this way to
        # conform to SearchEngine.search_sounds definition which must return SearchResults
        results = SolrResponseInterpreter(self.get_sounds_index().select(unicode(query)))
        return SearchResults(
            docs=results.docs,
            num_found=results.num_found,
            start=results.start,
            num_rows=results.num_rows,
            non_grouped_number_of_results=results.non_grouped_number_of_results,
            facets=results.facets,
            highlighting=results.highlighting,
            q_time=results.q_time
        )

    def get_random_sound_id(self):
        query = SolrQuery()
        rand_key = random.randint(1, 10000000)
        sort = ['random_%d asc' % rand_key]
        filter_query = 'is_explicit:0'
        query.set_query("*:*")
        query.set_query_options(start=0, rows=1, field_list=["id"], filter_query=filter_query, sort=sort)
        response = SolrResponseInterpreter(self.get_sounds_index().select(unicode(query)))
        docs = response.docs
        if docs:
            return int(docs[0]['id'])
        return 0

    # Forum posts methods

    def add_forum_posts_to_index(self, forum_post_objects):
        documents = [convert_post_to_search_engine_document(p) for p in forum_post_objects]
        self.get_forum_index().add(documents)
        if settings.DEBUG:
            # Sending the commit message generates server errors in production, we should investigate that... it could
            # be related with a different version of solr running locally. In any case, this line was added only
            # recently together with the refactoring of search engine backends so that we could force committing while
            # testing, but it is not needed in production
            self.get_forum_index().commit()

    def remove_forum_posts_from_index(self, forum_post_objects_or_ids):
        for post_object_or_id in forum_post_objects_or_ids:
            if type(post_object_or_id) != Post:
                post_id = post_object_or_id
            else:
                post_id = post_object_or_id.id
            self.get_forum_index().delete_by_id(post_id)
        if settings.DEBUG:
            # Sending the commit message generates server errors in production, we should investigate that... it could
            # be related with a different version of solr running locally. In any case, this line was added only
            # recently together with the refactoring of search engine backends so that we could force committing while
            # testing, but it is not needed in production
            self.get_forum_index().commit()

    def forum_post_exists_in_index(self, forum_post_object_or_id):
        if type(forum_post_object_or_id) != Post:
            post_id = forum_post_object_or_id
        else:
            post_id = forum_post_object_or_id.id
        response = self.search_forum_posts(query_filter='id:{}'.format(post_id), offset=0, num_posts=1)
        return response.num_found > 0

    def search_forum_posts(self, textual_query='', query_filter='', offset=0, current_page=None,
                           num_posts=settings.FORUM_POSTS_PER_PAGE, group_by_thread=True):
        query = SolrQuery()
        query.set_dismax_query(textual_query, query_fields=[("thread_title", 4),
                                                            ("post_body", 3),
                                                            ("thread_author", 3),
                                                            ("post_author", 3),
                                                            ("forum_name", 2)])
        query.set_highlighting_options_default(field_list=["post_body"],
                                               fragment_size=200,
                                               alternate_field="post_body",
                                               require_field_match=False,
                                               pre="<strong>",
                                               post="</strong>")
        if current_page is not None:
            offset = (current_page - 1) * num_posts
        query.set_query_options(start=offset,
                                rows=num_posts,
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
                                filter_query=query_filter,
                                sort=["thread_created desc"])

        if group_by_thread:
            query.set_group_field("thread_title_grouped")
            query.set_group_options(group_limit=30)

        # Do the query!
        # Note: we create a SearchResults with the same members as SolrResponseInterpreter. This would not be strictly
        # needed because SearchResults and SolrResponseInterpreter are virtually the same, but we do it in this way to
        # conform to SearchEngine.search_sounds definition which must return SearchResults
        results = SolrResponseInterpreter(self.get_forum_index().select(unicode(query)))
        return SearchResults(
            docs=results.docs,
            num_found=results.num_found,
            start=results.start,
            num_rows=results.num_rows,
            non_grouped_number_of_results=results.non_grouped_number_of_results,
            facets=results.facets,
            highlighting=results.highlighting,
            q_time=results.q_time
        )

    # Tag clouds methods

    def get_user_tags(self, username):
        query = SolrQuery()
        query.set_dismax_query('')
        filter_query = 'username:\"%s\"' % username
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=10, mincount=1)
        results = SolrResponseInterpreter(self.get_sounds_index().select(unicode(query)))
        return results.facets['tag']

    def get_pack_tags(self, username, pack_name):
        query = SolrQuery()
        query.set_dismax_query('')
        filter_query = 'username:\"%s\" pack:\"%s\"' % (username, pack_name)
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=20, mincount=1)
        results = SolrResponseInterpreter(self.get_sounds_index().select(unicode(query)))
        return results.facets['tag']
