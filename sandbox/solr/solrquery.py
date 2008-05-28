import urllib, urllib2
import simplejson
import itertools

class Multidict(dict):
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
        for (key, value) in itertools.ifilter(lambda (key,value): value != None, all_items()):
            if isinstance(value, bool):
                value = str(value).lower()

            if isinstance(value, str):
                value = value.encode('utf-8')

            yield (key, value)


class SolrQueryException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SolrQuery(object):
    def __init__ (self, url="http://localhost:8983/solr/", query_type=None, writer_type="json", indent=None):
        """
            url: query URL entry point
            query_type: Which handler to use when replying, default: default
            writer_type: Available types are: SolJSON, SolPHP, SolPython, SolRuby, XMLResponseFormat, XsltResponseWriter
            indent: format output with indentation or not
        """
        self.url = url
        
        # some default parameters
        self.params = {
            'qt': query_type,
            'wt': writer_type,
            'indent': indent
        }
    
    def set_query(self, query):
        self.params['q'] = query

    def set_query_options(self, start=None, rows=None, sort=None, filter_query=None, field_list=None):
        """
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

    def add_facet_field(self, field):
        """
            add facet field
        """
        self.params['facet'] = True
        try:
            self.params['facet.field'].append(field)
        except KeyError:
            self.params['facet.field'] = [field]
        
    def set_facet_query(self, query):
        """
            additional query for faceting
        """
        self.params['facet.query'] = query
    
    # set global faceting options for regular fields
    def set_global_facet_options(self, limit=None, offset=None, prefix=None, sort=None, mincount=None, count_missing=None, enum_cache_mindf=None):
        """
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
        """
            set per facet options... see set_global_facet_options() for parameter explanation
        """
        try:
            if field not in self.params['facet.field']:
                raise SolrQueryException, "setting facet options for field that doesn't exist"
        except KeyError:
            raise SolrQueryException, "you haven't defined any facet fields yet"
        
        self.params['f.%s.facet.limit' % field] = limit
        self.params['f.%s.facet.offset' % field] = offset
        self.params['f.%s.facet.prefix' % field] = prefix
        self.params['f.%s.facet.sort' % field] = sort
        self.params['f.%s.facet.mincount' % field] = mincount
        self.params['f.%s.facet.missing' % field] = count_missing

    def add_date_facet(self, field):
        """
            add date facet field
        """
        self.params['facet'] = True
        try:
            self.params['facet.date'].append(field)
        except KeyError:
            self.params['facet.date'] = [field]
    
    def set_global_date_facet_options(self, start=None, end=None, gap=None, hardened=None, count_other=None):
        """
            start: date start in DateMathParser syntax
            end: date end in DateMathParser syntax
            gap: size of slices of date range
            hardend: True: if gap doesn't devide range make last slice smaller. False: go out of bounds with last slice
            count_other: A tuple of other dates to count: before, after, between, none, all
        """
        self.params['facet.date.start'] = start
        self.params['facet.date.end'] = start
        self.params['facet.date.gap'] = gap
        self.params['facet.date.hardend'] = hardend
        self.params['facet.date.other'] = count_other

    def set_date_facet_options(self, field, start=None, end=None, gap=None, hardened=None, count_other=None):
        """
            set per facet date options... see set_global_date_facet_options() for parameter explanation
        """

        try:
            if field not in self.params['facet.date']:
                raise SolrQueryException, "setting date facet options for field that doesn't exist"
        except KeyError:
            raise SolrQueryException, "you haven't defined any date facet fields yet"

        self.params['f.%s.date.start' % field] = start
        self.params['f.%s.date.end' % field] = start
        self.params['f.%s.date.gap' % field] = gap
        self.params['f.%s.date.hardend' % field] = hardend
        self.params['f.%s.date.other' % field] = count_other
        
    def set_global_highlighting_options(self, field_list=None, snippets=None, fragment_size=None, merge_contiguous=None, require_field_match=None, max_analyzed_chars=None, alternate_field=None, max_alternate_field_length=None, pre=None, post=None, fragmenter=None, use_phrase_highlighter=None, regex_slop=None, regex_pattern=None, regex_max_analyzed_chars=None):
        """
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
        """
            set per field highlighting options... see set_global_highlighting_options() for parameter explanation
        """
        
        try:
            if field not in self.params['hl.fl']:
                raise SolrQueryException, "setting highlighting options for field that doesn't exist"
        except KeyError:
            raise SolrQueryException, "you haven't defined any highlighting fields yet"

        self.params['f.%s.hl.fl.snippets' % field] = snippets
        self.params['f.%s.hl.fragsize' % field] = fragment_size
        self.params['f.%s.hl.mergeContiguous' % field] = merge_contiguous
        self.params['f.%s.hl.alternateField' % field] = alternate_field
        self.params['f.%s.hl.simple.pre' % field] = pre
        self.params['f.%s.hl.simple.post' % field] = post
        
    def get_query_string(self):
        return urllib.urlencode(Multidict(self.params))
        
    def do_query(self):
        headers = {
            #'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        req = urllib2.Request(self.url, self.get_query_string(), headers)
        
        try:
            response = urllib2.urlopen(req)
        except URLError:
            print e.reason
    
        # datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        
        if self.params["wt"] == "json":
            return simplejson.load(response)
        else:
            return response
