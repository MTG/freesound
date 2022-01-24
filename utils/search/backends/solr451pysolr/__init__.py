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
#     See AUTHORS file.
#

import json
import math
import types
import urllib
from datetime import date, datetime
from socket import error
from time import strptime
from xml.etree import cElementTree as ET

import httplib
import pysolr
import urlparse

from django.conf import settings
from utils.text import remove_control_chars
from utils.search import Multidict, SearchEngineBase, SearchEngineException, SERACH_INDEX_SOUNDS, SERACH_INDEX_FORUM


class SolrQuery(object):
    """A wrapper around a lot of Solr query funcionality.
    """

    def __init__ (self, query_type=None, writer_type="json", indent=None, debug_query=None):
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

    def set_dismax_query(self, query, query_fields=None, minimum_match=None, phrase_fields=None, phrase_slop=None, query_phrase_slop=None, tie_breaker=None, boost_query=None, boost_functions=None):
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
                    qf.append("^".join(map(str,f)))
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
    def set_facet_options_default(self, limit=None, offset=None, prefix=None, sort=None, mincount=None, count_missing=None, enum_cache_mindf=None):
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
    def set_facet_options(self, field, prefix=None, sort=None, limit=None, offset=None, mincount=None, count_missing=None):
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

    def set_highlighting_options_default(self, field_list=None, snippets=None, fragment_size=None, merge_contiguous=None, require_field_match=None, max_analyzed_chars=None, alternate_field=None, max_alternate_field_length=None, pre=None, post=None, fragmenter=None, use_phrase_highlighter=None, regex_slop=None, regex_pattern=None, regex_max_analyzed_chars=None):
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
        #self.params['hl.formatter'] = # only valid one is "simple" right now
        self.params['hl.simple.pre'] = pre
        self.params['hl.simple.post'] = post
        self.params['hl.fragmenter'] = fragmenter
        self.params['hl.usePhraseHighlighter'] = use_phrase_highlighter
        self.params['hl.regex.slop'] = regex_slop
        self.params['hl.regex.pattern'] = regex_pattern
        self.params['hl.regex.maxAnalyzedChars'] = regex_max_analyzed_chars

    def set_highlighting_options(self, field, snippets=None, fragment_size=None, merge_contiguous=None, alternate_field=None, pre=None, post=None):
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

    # pysolr
    def as_dict(self):
        params = {k: v for k, v in self.params.iteritems() if v is not None}
        for k, v in params.iteritems():
            if type(v) == types.BooleanType:
                params[k] = json.dumps(v)
        return params

    def set_group_field(self, group_field=None):
        self.params['group.field'] = group_field

    def set_group_options(self, group_func=None, group_query=None, group_rows=10, group_start=0, group_limit=1, group_offset=0, group_sort=None, group_sort_ingroup=None, group_format='grouped', group_main=False, group_num_groups=True, group_cache_percent=0, group_truncate=False):
        self.params['group'] = True
        self.params['group.func'] = group_func
        self.params['group.query'] = group_query
        self.params['group.rows'] = group_rows
        self.params['group.start'] = group_start
        self.params['group.limit'] = group_limit
        self.params['group.offset'] = group_offset
        self.params['group.sort'] = group_sort
        self.params['group.sort.ingroup']  = group_sort_ingroup
        self.params['group.format'] = group_format
        self.params['group.main'] = group_main
        self.params['group.ngroups'] = group_num_groups
        self.params['group.truncate'] = group_truncate
        self.params['group.cache.percent'] = group_cache_percent


def encode_value(value):
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
    return value


def encode_list_dicts(list_dicts):
    return [dict((k, encode_value(v)) for (k, v) in d.items()) for d in list_dicts]



class SolrResponseInterpreter(object):
    def __init__(self, response):
        response = response.raw_response

        if "grouped" in response:
            if "thread_title_grouped" in response["grouped"].keys():
                self.docs = response["grouped"]["thread_title_grouped"]["groups"]
                self.start = response["responseHeader"]["params"]["start"]
                self.num_rows = len(self.docs) # response["responseHeader"]["params"]["rows"]
                self.num_found = response["grouped"]["thread_title_grouped"]["ngroups"]
                self.non_grouped_number_of_matches = response["grouped"]["thread_title_grouped"]["matches"]
            elif "grouping_pack" in response["grouped"].keys():
                #self.docs = response["grouped"]["pack"]["groups"]
                self.docs = [{
                                 'id': group['doclist']['docs'][0]['id'],
                                 'more_from_pack':group['doclist']['numFound']-1,
                                 'pack_name':group['groupValue'][group['groupValue'].find("_")+1:],
                                 'pack_id':group['groupValue'][:group['groupValue'].find("_")],
                                 'other_ids': [doc['id'] for doc in group['doclist']['docs'][1:]]
                             } for group in response["grouped"]["grouping_pack"]["groups"] if group['groupValue'] != None ]
                self.start = response["responseHeader"]["params"]["start"]
                self.num_rows = len(self.docs) # response["responseHeader"]["params"]["rows"]
                self.num_found = response["grouped"]["grouping_pack"]["ngroups"]#["matches"]#
                self.non_grouped_number_of_matches = response["grouped"]["grouping_pack"]["matches"]
        else:
            self.docs = response["response"]["docs"]
            self.start = response["response"]["start"]
            self.num_rows = len(self.docs)
            self.num_found = response["response"]["numFound"]
            self.non_grouped_number_of_matches = -1

        self.q_time = response["responseHeader"]["QTime"]
        try:
            self.facets = response["facet_counts"]["facet_fields"]
        except KeyError:
            self.facets = {}

        """Facets are given in a list: [facet, number, facet, number, None, number] where the last one
        is the mising field count. Converting all of them to a dict for easier usage:
        {facet:number, facet:number, ..., None:number}
        """
        for facet, fields in self.facets.items():
            self.facets[facet] = [(fields[index], fields[index+1]) for index in range(0, len(fields), 2)]

        try:
            self.highlighting = response["highlighting"]
        except KeyError:
            self.highlighting = {}

    def display(self):
        print "Solr response:"
        print "\tGlobal parameters:"
        print "\t\t%d docs found in %d ms" % (self.num_found, self.q_time)
        print "\t\treturning %d docs starting from row %d" % (self.num_rows, self.start)
        print
        print "\tFaceting:"
        print "\t\tNr facets:", len(self.facets)
        print "\t\t\t%s" % "\n\t\t\t".join(["%s with %d entries" % (k,len(v)) for (k,v) in self.facets.items()])
        print
        print "\tHighlighting"
        print "\t\tNr highlighted docs:", len(self.highlighting)
        print
        print "\tDocuments:"
        print "\t\tNr docs found:", self.num_rows
        if self.num_rows > 0:
            print "\t\tPrinting one doc:"
            self.pp(self.docs[0], 3)

    def pp(self, d, indent=0):
        """A pretty print for general data. Tried pprint but just couldn't get it right
        """
        i = "\t"*indent
        if isinstance(d, dict):
            print i, "{"
            for (k,v) in d.items():
                self.pp(k, indent+1)
                print ":"
                self.pp(v, indent+2)
                print
            print i, "}",
        elif isinstance(d, tuple):
            print i, "("
            for v in d:
                self.pp(v, indent+1)
                print
            print i, ")",
        elif isinstance(d, list):
            print i, "["
            for v in d:
                self.pp(v, indent+1)
                print
            print i, "]",
        elif isinstance(d, basestring):
            print i, "\"%s\"" % d,
        else:
            print i, d,


class SolrResponseInterpreterPaginator(object):
    def __init__(self, interpreter, num_per_page):
        self.num_per_page = num_per_page
        self.interpreter = interpreter
        self.count = interpreter.num_found
        self.num_pages = interpreter.num_found / num_per_page + int(interpreter.num_found % num_per_page != 0)
        self.page_range = range(1, self.num_pages + 1)

    def page(self, page_num):
        has_next = page_num < self.num_pages
        has_previous = page_num > 1 and page_num <= self.num_pages
        return {'object_list': self.interpreter.docs,
                'has_next': has_next,
                'has_previous': has_previous,
                'has_other_pages': has_next or has_previous,
                'next_page_number': page_num + 1,
                'previous_page_number': page_num - 1
                }


class Solr451PySolrSearchEngine(SearchEngineBase):

    def __init__(self, index_name):
        super(Solr451PySolrSearchEngine, self).__init__(index_name)
        
        if self.index_name == SERACH_INDEX_SOUNDS:
            url = settings.SOLR_URL
        elif self.index_name == SERACH_INDEX_FORUM:
            url = settings.SOLR_FORUM_URL
        else:
            raise SearchEngineException("No index with that name")
        # TODO: check if we need specific settings here when creating the Solr object from pysolr (e.g. always_commit, timeout, ...)
        self.pysolr = pysolr.Solr(url)

    def search(self, query):
        try:
            return SolrResponseInterpreter(self.pysolr.search(**query.as_dict()))
        except pysolr.SolrError as e:
            raise SearchEngineException, str(e)
    
    def return_paginator(self, results, num_per_page):
        return SolrResponseInterpreterPaginator(results, num_per_page)

    def add_to_index(self, docs):
        try:
            self.pysolr.add(encode_list_dicts(docs))
        except pysolr.SolrError as e:
            raise SearchEngineException, str(e)

    def remove_from_index(self, document_id):
        try:
            self.pysolr.delete(id=id)
        except pysolr.SolrError as e:
            raise SearchEngineException, str(e)

    def remove_from_index_by_query(self, query):
        try:
            self.pysolr.delete(q=query)
        except pysolr.SolrError as e:
            raise SearchEngineException, str(e)

    def remove_from_index_by_ids(self, document_ids):
        document_ids_query = ' OR '.join(['id:{0}'.format(document_id) for document_id in document_ids])
        self.solr.delete_by_query(document_ids_query)

    def get_query_manager(self):
        return SolrQuery()

    def convert_sound_to_search_engine_document(self, sound):
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
            document["grouping_pack"] = str(getattr(sound, "pack_id")) + "_" + remove_control_chars(getattr(sound, "pack_name"))
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

        # Audio Commons analysis
        # NOTE: as the sound object here is the one returned by SoundManager.bulk_query_solr, it will have the Audio Commons
        # descriptor fields under a property called 'ac_analysis'.
        ac_analysis = getattr(sound, "ac_analysis")
        if ac_analysis is not None:
            # If analysis is present, index all existing analysis fields under Solr's dynamic fields "*_i", "*_d", "*_s"
            # and "*_b" depending on the value's type. Also add Audio Commons prefix.
            for key, value in ac_analysis.items():
                suffix = settings.SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.get(type(value), None)
                if suffix:
                    document['{0}{1}{2}'.format(settings.AUDIOCOMMONS_DESCRIPTOR_PREFIX, key, suffix)] = value

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
