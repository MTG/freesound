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

from datetime import datetime, date
from time import strptime
from xml.etree import cElementTree as ET
import itertools, re, urllib
import httplib, urlparse
import cjson
from socket import error
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
        for (key, value) in itertools.ifilter(lambda (key,value): value != None and value != "", all_items()):
            if isinstance(value, bool):
                value = unicode(value).lower()
            else:
                value = unicode(value).encode('utf-8')

            yield (key, value)


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
                raise SolrException, "setting facet options for field that doesn't exist"
        except KeyError:
            raise SolrException, "you haven't defined any facet fields yet"

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
                raise SolrException, "setting date facet options for field that doesn't exist"
        except KeyError:
            raise SolrException, "you haven't defined any date facet fields yet"

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
                raise SolrException, "setting highlighting options for field that doesn't exist"
        except KeyError:
            raise SolrException, "you haven't defined any highlighting fields yet"

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

    def set_group_options(self, group_func=None, group_query=None, group_rows=10, group_start=0, group_limit=1, group_offset=0, group_sort=None, group_sort_ingroup=None, group_format='grouped', group_main=False, group_num_groups=True, group_cache_percent=0):
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
        #return self._decode_dates(json.load(response_object))
        return self._decode_dates(cjson.decode(unicode(response_object.read(),'utf-8'))) #@UndefinedVariable

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


class SolrException(Exception):
    pass


class Solr(object):
    def __init__(self, url="http://localhost:8983/solr", auto_commit=True, verbose=False, persistent=False, encoder=BaseSolrAddEncoder(), decoder=SolrJsonResponseDecoder()):
        url_split = urlparse.urlparse(url)

        self.host = url_split.hostname
        self.port = url_split.port
        self.path = url_split.path.rstrip('/')

        self.decoder = decoder
        self.encoder = encoder
        self.verbose = verbose
        self.auto_commit = auto_commit

        self.persistent = persistent

        if self.persistent:
            self.conn = httplib.HTTPConnection(self.host, self.port)

    def _request(self, query_string="", message=""):
        if query_string.startswith("suggest"):
            path = '%s/%s' % (self.path, query_string) 
        elif query_string != "":
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
            raise SolrException, response.reason
        
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
        except error, e:
            raise SolrException, e
        #if self.auto_commit:
        #    self.commit()

    def delete_by_id(self, id):
        self._request(message=u'<delete><id>%s</id></delete>' % unicode(id))
        #if self.auto_commit:
        #    self.commit()

    def delete_by_query(self, query):
        self._request(message=u'<delete><query>%s</query></delete>' % unicode(query))
        #if self.auto_commit:
        #    self.commit()

    def commit(self, wait_flush=True, wait_searcher=True):
        message = ET.Element('commit')
        message.set("waitFlush", str(wait_flush).lower())
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
                self.docs = response["grouped"]["thread_title_grouped"]["groups"]
                self.start = response["responseHeader"]["params"]["start"]
                self.num_rows = len(self.docs) # response["responseHeader"]["params"]["rows"]
                self.num_found = response["grouped"]["thread_title_grouped"]["ngroups"]
                self.non_grouped_number_of_matches = response["grouped"]["thread_title_grouped"]["matches"]
            elif "grouping_pack" in response["grouped"].keys():
                #self.docs = response["grouped"]["pack"]["groups"]
                self.docs = [{'id': group['doclist']['docs'][0]['id'], 'more_from_pack':group['doclist']['numFound']-1, 'pack_name':group['groupValue'][group['groupValue'].find("_")+1:], 'pack_id':group['groupValue'][:group['groupValue'].find("_")]} for group in response["grouped"]["grouping_pack"]["groups"] if group['groupValue'] != None ]
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
        object_list = self.interpreter.docs
        has_next = page_num < self.num_pages
        has_previous = page_num > 1 and page_num <= self.num_pages
        has_other_pages = has_next or has_previous
        next_page_number = page_num + 1
        previous_page_number = page_num - 1
        #start_index = self.interpreter.start
        #end_index = self.interpreter.start + self.interpreter.num_found
        return locals()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
