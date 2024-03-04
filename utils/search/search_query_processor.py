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
import urllib

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
import luqum.tree
from luqum.parser import parser
from luqum.pretty import prettify

from utils.clustering_utilities import get_ids_in_cluster
from utils.encryption import create_hash
from utils.search.backends.solr555pysolr import FIELD_NAMES_MAP
from utils.search.search_sounds import allow_beta_search_features
from .search_query_processor_options_base import SearchOptionStr, SearchOptionChoice, \
    SearchOptionInt, SearchOptionBool, SearchOptionRange, SearchOptionMultipleChoice


# --- Search options objects for Freesound search

class SearchOptionQuery(SearchOptionStr):
    name = 'query'
    query_param_name = 'q'

    def should_be_disabled(self):
        return bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo))


class SearchOptionSort(SearchOptionChoice):
    name = 'sort_by'
    label = 'Sort by'
    value_default = settings.SEARCH_SOUNDS_SORT_DEFAULT
    choices = [(option, option) for option in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB]
    query_param_name = 's'

    def should_be_disabled(self):
        return bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo))
    
    def get_default_value(self):
        if self.search_query_processor.get_option_value(SearchOptionQuery) == '':
            # When making empty queries and no sorting is specified, automatically set sort to "created desc" as
            # relevance score based sorting makes no sense
            return settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST
        return self.value_default


class SearchOptionPage(SearchOptionInt):
    name= 'page'
    query_param_name = 'page'
    value_default = 1

    def get_value_to_apply(self):
        # Force return 1 in map mode
        if self.search_query_processor.get_option_value(SearchOptionMapMode):
            return 1
        return super().get_value_to_apply()


class SearchOptionDuration(SearchOptionRange):
    name = 'duration'
    label = 'Duration'
    search_engine_field_name = 'duration'
    query_param_min = 'd0'
    query_param_max = 'd1'
    value_default = ['0', '*']


class SearchOptionIsRemix(SearchOptionBool):
    name= 'is_remix'
    label= 'Only remix sounds'
    query_param_name = 'r'
    search_engine_field_name = 'in_remix_group'
    help_text=  'Only find sounds that are a remix of other sounds or have been remixed'


class SearchOptionGroupByPack(SearchOptionBool):
    name= 'group_by_pack'
    label= 'Group sounds by pack'
    query_param_name = 'g'
    help_text= 'Group search results so that multiple sounds of the same pack only represent one item'
    value_default = True

    def get_value_to_apply(self):
        # Force return True if display_as_packs is enabled, and False if map_mode is enabled
        if self.search_query_processor.has_filter_with_name('grouping_pack'):
            return False
        elif self.search_query_processor.get_option_value(SearchOptionDisplayResultsAsPacks):
            return True
        elif self.search_query_processor.get_option_value(SearchOptionMapMode):
            return False
        return super().get_value_to_apply()

    def should_be_disabled(self):
        return self.search_query_processor.has_filter_with_name('grouping_pack') or \
            self.search_query_processor.get_option_value(SearchOptionDisplayResultsAsPacks) or \
            self.search_query_processor.get_option_value(SearchOptionMapMode)


class SearchOptionDisplayResultsAsPacks(SearchOptionBool):
    name= 'display_as_packs'
    label= 'Display results as packs'
    query_param_name = 'dp'
    help_text= 'Display search results as packs rather than individual sounds'

    def get_value_to_apply(self):
        # Force return False if a pack filter is active
        if self.search_query_processor.has_filter_with_name('grouping_pack'):
            return False
        return super().get_value_to_apply()

    def should_be_disabled(self):
        return self.search_query_processor.has_filter_with_name('grouping_pack') or self.search_query_processor.get_option_value(SearchOptionMapMode)


class SearchOptionGridMode(SearchOptionBool):
    name= 'grid_mode'
    label= 'Display results in grid'
    query_param_name = 'cm'
    help_text= 'Display search results in a grid so that more sounds are visible per search results page'

    def get_default_value(self):
        if self.search_query_processor.request.user.is_authenticated:
            return self.search_query_processor.request.user.profile.use_compact_mode
        return False
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionMapMode)


class SearchOptionMapMode(SearchOptionBool):
    name= 'map_mode'
    label= 'Display results in map'
    query_param_name = 'mm'
    help_text= 'Display search results in a map'


class SearchOptionIsGeotagged(SearchOptionBool):
    name = 'is_geotagged'
    label = 'Only geotagged sounds'
    query_param_name = 'ig'
    search_engine_field_name = 'is_geotagged'
    help_text= 'Only find sounds that have geolocation information'
    
    def as_filter(self):
        # Force render filter True if map_mode is enabled
        return super().as_filter() if not self.search_query_processor.get_option_value(SearchOptionMapMode) else f'{self.search_engine_field_name}:1'
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionMapMode)


class SearchOptionSimilarTo(SearchOptionStr):
    # NOTE: implement this as SearchOptionStr instead of SearchOptionInt so it supports using vectors in format [x0,x1,x2,...,xn]
    name= 'similar_to'
    query_param_name = 'st'


class SearchOptionTagsMode(SearchOptionBool):
    name= 'tags_mode'

    def get_value_from_request(self):
        # Tags mode is a special option which is not passed as a query parameter but is inferred from the URL
        return reverse('tags') in self.request.path


class SearchOptionComputeClusters(SearchOptionBool):
    name= 'compute_clusters'
    label = 'Cluster results by similarity'
    query_param_name = 'cc'


class SearchOptionClusterId(SearchOptionInt):
    name= 'cluster_id'
    query_param_name = 'cid'


class SearchOptionSearchIn(SearchOptionMultipleChoice):
    name = 'search_in'
    label = 'Search in'
    value_default = []
    query_param_name_prefix = 'si'
    choices = [
        (settings.SEARCH_SOUNDS_FIELD_TAGS, 'Tags'),
        (settings.SEARCH_SOUNDS_FIELD_NAME, 'Sound name'),
        (settings.SEARCH_SOUNDS_FIELD_DESCRIPTION, 'Description'),
        (settings.SEARCH_SOUNDS_FIELD_PACK_NAME, 'Pack name'),
        (settings.SEARCH_SOUNDS_FIELD_ID, 'Sound ID'),
        (settings.SEARCH_SOUNDS_FIELD_USER_NAME, 'Username')
    ]
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionTagsMode) or bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo))


class SearchOptionFieldWeights(SearchOptionStr):
    name= 'field_weights'
    query_param_name = 'w'
    value_default = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS

    def get_value_from_request(self):
        """param weights can be used to specify custom field weights with this format 
        w=field_name1:integer_weight1,field_name2:integrer_weight2, eg: w=name:4,tags:1
        ideally, field names should any of those specified in settings.SEARCH_SOUNDS_FIELD_*
        so the search engine can implement ways to translate the "web names" to "search engine"
        names if needed.
        """
        weights_param = self.request.GET.get(self.query_param_name, None)
        parsed_field_weights = {}
        if weights_param:
            for part in weights_param.split(','):
                if ':' in part:
                    try:
                        field_name = part.split(':')[0]
                        weight = int(part.split(':')[1])
                        parsed_field_weights[field_name] = weight
                    except Exception:
                        # If format is wrong, ignore parameter
                        pass
        if len(parsed_field_weights):
            return parsed_field_weights
        else:
            return None
        
    def as_URL_params(self):
        value_for_url = ''
        for field, weight in self.value.items():
            value_for_url += f'{field}:{weight},'
        if value_for_url.endswith(','):
            value_for_url = value_for_url[:-1]
        return {self.query_param_name : value_for_url}
    

# --- Search query processor class

class SearchQueryProcessor(object):
    """The SearchQueryProcessor class is used to parse and process search query information from a request object and
    compute a number of useful items for displaying search information in templates, constructing search URLs, and 
    preparing search options to be passed to the backend search engine.
    """
    request = None
    options = {}
    avaialable_options = [
        SearchOptionQuery,
        SearchOptionSort,
        SearchOptionPage,
        SearchOptionSearchIn,
        SearchOptionDuration,
        SearchOptionIsGeotagged,
        SearchOptionIsRemix,
        SearchOptionGroupByPack,
        SearchOptionDisplayResultsAsPacks,
        SearchOptionGridMode,
        SearchOptionMapMode,
        SearchOptionTagsMode,
        SearchOptionSimilarTo,
        SearchOptionFieldWeights,
        SearchOptionComputeClusters,
        SearchOptionClusterId
    ]
    non_advanced_options = [
        SearchOptionQuery, 
        SearchOptionSort, 
        SearchOptionPage, 
        SearchOptionClusterId,
        SearchOptionTagsMode,
        SearchOptionDisplayResultsAsPacks,
        SearchOptionMapMode,
        SearchOptionGridMode
    ]
    errors = ''

    def __init__(self, request, facets=None):
        """Initializes the SearchQueryProcessor object by parsing data from the request and setting up search options.

        Args:
            request (django.http.HttpRequest): request object from which to parse search options
            facets (dict, optional): dictionary with facet options to be used in the search. If not provided, default
              facets will be used. Default is None.
        """

        # Store the request and the facets argument as it will be used later
        self.request = request
        if facets is None:
            self.facets = settings.SEARCH_SOUNDS_DEFAULT_FACETS.copy()  # NOTE: not sure if .copy() is needed here to avoid mutating original setting
        else:
            self.facets = facets
        
        # Get filter and parse it. Make sure it is iterable (even if it only has one element)
        self.f = urllib.parse.unquote(request.GET.get('f', '')).strip().lstrip()
        if self.f:
            try:
                f_parsed = parser.parse(self.f)
                if type(f_parsed) == luqum.tree.SearchField:
                    self.f_parsed = [f_parsed]
                else:
                    self.f_parsed = f_parsed.children
            except luqum.exceptions.ParseError as e:
                self.errors = f"Filter parsing error: {e}"
                self.f_parsed = []
        else:
            self.f_parsed = []
       
        # Remove duplicate filters if any
        nodes_in_filter = []
        f_parsed_no_duplicates = []
        for node in self.f_parsed:
            if node not in nodes_in_filter:
                nodes_in_filter.append(node)
                f_parsed_no_duplicates.append(node)
        self.f_parsed = f_parsed_no_duplicates

        # Implement compatibilty with old URLs in which "duration"/"is remix"/"is geotagged" options were passed as raw filters.
        # If any of these filters are present, we parse them to get their values and modify the request to simulate the data being 
        # passed in the new expected way (through request parameters). If present, we also remove these filters from the f_parsed object.
        values_to_update = {}
        for field_name in [SearchOptionIsRemix.search_engine_field_name, SearchOptionIsGeotagged.search_engine_field_name]:        
            for node in self.f_parsed:
                if type(node) == luqum.tree.SearchField:
                    if node.name == field_name:
                        values_to_update[field_name] = str(node.expr) == '1'
                        self.f_parsed = [f for f in self.f_parsed if f != node]

        field_name = SearchOptionDuration.search_engine_field_name
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name == field_name:
                    # node.expr is expected to be of type luqum.tree.Range
                    values_to_update[field_name] = [str(node.expr.low), str(node.expr.high)]
                    self.f_parsed = [f for f in self.f_parsed if f != node]

        if values_to_update:
            self.request.GET = self.request.GET.copy()
            if SearchOptionIsRemix.search_engine_field_name in values_to_update:
                self.request.GET[SearchOptionIsRemix.query_param_name] = '1' if values_to_update[SearchOptionIsRemix.search_engine_field_name] else '0'
            if SearchOptionIsGeotagged.search_engine_field_name in values_to_update:
                self.request.GET[SearchOptionIsGeotagged.query_param_name] = '1' if values_to_update[SearchOptionIsGeotagged.search_engine_field_name] else '0'
            if SearchOptionDuration.search_engine_field_name in values_to_update:
                self.request.GET[SearchOptionDuration.query_param_min] = values_to_update[SearchOptionDuration.search_engine_field_name][0]
                self.request.GET[SearchOptionDuration.query_param_max] = values_to_update[SearchOptionDuration.search_engine_field_name][1]

        # Create SearchOption objects and load their values form the request
        for optionClass in self.avaialable_options:
            option = optionClass(self)
            self.options[option.name] = option

        # Some of the filters included in the search query (in f_parsed) might belog to filters which are added by SearchOption objects, but some others might
        # be filters added by search facets or "raw filters" directly added to the URL by the user. Some methods of the SearchQueryProcessor need to know which
        # filters belong to search options, so we pre-compute the list of non-option filters here as a list of (field,value) tuples. For example, if
        # a query has the filter "f=is_geotagged:1 samplerate:44100", self.non_option_filters will be [('samplerate', '44100')] as "is_geotagged" is a filter managed
        # by the SearchOptionIsGeotagged option, but "samplerate" is a facet filter and not managed by a search option.
        self.non_option_filters = []
        search_engine_field_names_used_in_options = [option.search_engine_field_name for option in self.options.values() if hasattr(option, 'search_engine_field_name')]
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name not in search_engine_field_names_used_in_options:
                    self.non_option_filters.append((
                        node.name,
                        str(node.expr)
                    ))

    # Filter-related methods

    def get_active_filters(self, include_filters_from_options=True, 
                           include_non_option_filters=True, 
                           include_filters_from_facets=True, 
                           extra_filters=None, 
                           ignore_filters=None):
        """Returns a list of all filters which are active in the query in a ["field:value", "field:value", ...] format. This method
        also allows to add extra filters to the list or ignore some of the existing filters.

        Args:
            include_filters_from_options (bool, optional): If True, filters from search options will be included. Default is True.
            include_non_option_filters (bool, optional): If True, filters from non-option filters will be included. Default is True.
            include_filters_from_facets (bool, optional): If True, filters from search facets will be included. Note that if 
              include_non_option_filters is set to False, include_filters_from_facets will have no effect as facet filters are part of
              non-option filters. Default is True.
            extra_filters (list, optional): List of extra filters to be added. Each filter should be a string in the format "field:value",
              e.g.: extra_filters=["tag:tagname"]. Default is None.
            ignore_filters (list, optional): List of filters to be ignored. Each filter should be a string in the format "field:value",
              e.g.: ignore_filters=["tag:tagname"]. Default is None.
        """
        # Create initial list of the active filters according to the types of filters that are requested to be included
        ff = []
        if include_filters_from_options:
            for option in self.options.values():
                fit = option.as_filter()
                if fit is not None:
                    ff.append(fit)
        if include_non_option_filters:
            for non_option_filter in self.non_option_filters:
                should_be_included = True
                facet_search_engine_field_names = [FIELD_NAMES_MAP[f] for f in self.facets.keys()]
                if not include_filters_from_facets and non_option_filter[0] in facet_search_engine_field_names:
                    should_be_included = False
                if should_be_included:
                    ff.append(f'{non_option_filter[0]}:{non_option_filter[1]}')
            
        # Remove ignored filters
        if ignore_filters is not None:
            ff = [f for f in ff if f not in ignore_filters]

        # Add extra filter
        if extra_filters is not None:
            ff += extra_filters
        return ff

    def get_num_active_filters(self, include_filters_from_options=True, 
                               include_non_option_filters=True, 
                               include_filters_from_facets=True, 
                               extra_filters=None, 
                               ignore_filters=None):
        """Returns the number of active filters in the query. This method has the same parameters of self.get_active_filters.
        """
        return len(self.get_active_filters(include_filters_from_options=include_filters_from_options, include_non_option_filters=include_non_option_filters,
                                           include_filters_from_facets=include_filters_from_facets, extra_filters=extra_filters, ignore_filters=ignore_filters))

    def get_filters_data_to_display_in_search_results_page(self):
        """Returns a list of filters to be displayed in the search results page. Each element in the list is a tuple with (field, value, remove_url), where
        field is the name of the field, value is the value of the filter, and remove_url is the URL thta should be followed to remove the filter from the query.
        """
        filters_data = []
        for name, value in self.non_option_filters:
            filter_data = [name, value, self.get_url(remove_filters=[f'{name}:{value}'])]
            if name == 'grouping_pack':
                # There is a special case for the grouping_pack filter in which we only want to display the name of the pack and not the ID
                filter_data[0] = 'pack'
                if value.startswith('"'):
                    filter_data[1] = '"'+ value[value.find("_")+1:]
                else:
                    filter_data[1] = value[value.find("_")+1:]

            filters_data.append(filter_data)
        return filters_data
    
    def has_filter_with_name(self, filter_name):
        """Returns True if the parsed filter has a filter with the given name.
        """
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name == filter_name:
                    return True
        return False
    
    def get_tags_in_filters(self):
        """Returns a list of tags that are being used in the filters. E.g.: ["tag1", "tag2"]
        """
        tags_in_filter = []
        for field, value in self.non_option_filters:
            if field == 'tag':
                if value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]  # Remove quotes
                tags_in_filter.append(value)
        return tags_in_filter
    
    def get_filter_string_for_search_engine(self, 
                                            include_filters_from_options=True, 
                                            include_non_option_filters=True, 
                                            include_filters_from_facets=True, 
                                            extra_filters=None, 
                                            ignore_filters=None):
        """Returns a filter string with the proper format to be used by the search engine. This method has the same parameters of self.get_active_filters
        to indicate which filters should or should not be included. By default all filters are included. En example of a filter string returned by that
        method could be something like: 'duration:[0.25 TO 20] tag:"tag1" is_geotagged:1 (id:1 OR id:2 OR id:3) tag:"tag2"'
        """
        ff = self.get_active_filters(include_filters_from_options=include_filters_from_options, include_non_option_filters=include_non_option_filters, 
                                     include_filters_from_facets=include_filters_from_facets, extra_filters=extra_filters, ignore_filters=ignore_filters)
        return ' '.join(ff)
    
    def get_filter_string_for_url(self, extra_filters=None, ignore_filters=None):
        """Returns a filter string to be used in search URLs. Note that filters which are managed by SearchOption objects must not be included here as
        these are added to URLs as query parameters. Note that this method also includes the "extra_filters" and "ignore_filters" parameters from
        self.get_active_filters as this is useful to create URLs to add or remove filters."""
        return self.get_filter_string_for_search_engine(include_filters_from_options=False, extra_filters=extra_filters, ignore_filters=ignore_filters)

    # Other util methods
        
    def contains_active_advanced_search_options(self):
        """Returns true if the query has any active options which belong to the "advanced search" panel
        Also returns true if the query has active undocumented options which are hidden in the advanced 
        search panel but that are allowed as "power user" options
        """
        for option in self.options.values():
            if option.name not in [opt.name for opt in self.non_advanced_options]:
                if option.set_in_request:
                    if not option.is_default_value:
                        return True
        return False

    def get_clustering_data_cache_key(self, include_filters_from_facets=False):
        """Generates a cache key used to store clustering results in the cache. Note that the key excludes facet filters
        by default because clusters are computed on the subset of results BEFORE applying the facet filters (this is by
        design to avoid recomputing clusters when changing facets). However, the key can be generated including facets as
        well because in some occasions we want to store clustering-related data which does depend on the facet filters which
        are applied after the main clustaering computation.

        Args:
            include_filters_from_facets (bool): If True, the key will include filters from facets as well. Default is False.
              Filters that are included in facets correspond to the facet fields defined in self.facets, which defaults to
              settings.SEARCH_SOUNDS_DEFAULT_FACETS.

        Returns:
            str: Cache key for the clustering data
        """
        query_filter = self.get_filter_string_for_search_engine(include_filters_from_facets=include_filters_from_facets)
        key = f'cluster-results-{self.get_option_value(SearchOptionQuery)}-' + \
              f'{query_filter}-{self.get_option_value(SearchOptionSort)}-' + \
              f'{self.get_option_value(SearchOptionGroupByPack)}'
        return create_hash(key, limit=32)

    def get_textual_description(self):
        """Returns a textual description of the search query, e.g.: "cat (some filters applied)"'
        """
        query_description = ''
        textual_query = self.get_option_value(SearchOptionQuery)
        if textual_query:
            query_description = f'"{textual_query}"'
        else:
            query_description = 'Empty query'
        num_filters = self.get_num_active_filters()
        if num_filters:
            query_description += f' with {num_filters} filter{"" if num_filters == 1 else "s"}'
        return query_description
    
    def print(self):
        """Prints the SearchQueryProcessor object in a somewhat human readable format
        """
        print('\nSEARCH QUERY')
        print('f_parsed:')
        print(prettify(self.f_parsed))
        if self.errors:
            print('errors:')
            print(self.errors)
        print('options:')
        for option in self.options.values():
            print('-', option)
        if self.non_option_filters:
            print('non_option_filters:')
            for filter in self.non_option_filters:
                print('-', f'{filter[0]}={filter[1]}')
                
    def as_query_params(self, exclude_facet_filters=False):
        """Returns a dictionary with the search options and filters to be used as parameters for the SearchEngine.search_sounds method.
        This method post-processes the data loaded into the SearchQueryProcessor to generate an approptiate query_params dict. Note that
        this method includes some complex logic that takes into account the interaction with some option values to calculate the
        query_params values to be used by the search engine. 

        Args:
            exclude_facet_filters (bool, optional): If True, facet filters will not be used to create the query_params dict. Default is False.
              This is useful as part of the clustering features for which we want to make a query which ignores the facet filters provided in the URL.

        Returns:
            dict: Dictionary with the query parameters to be used by the SearchEngine.search_sounds method.
        """

        # Filter field weights by "search in" options
        field_weights = self.get_option_value(SearchOptionFieldWeights)
        search_in_value = self.get_option_value(SearchOptionSearchIn)
        if search_in_value:
            field_weights = {field: weight for field, weight in field_weights.items() if field in search_in_value}
        
        # Number of sounds
        if self.get_option_value(SearchOptionDisplayResultsAsPacks):
            # When displaying results as packs, always return the same number regardless of the compact mode setting
            # This because returning a large number of packs makes the search page very slow
            # If we optimize pack search, this should be removed
            num_sounds = settings.SOUNDS_PER_PAGE
        else:
            num_sounds = settings.SOUNDS_PER_PAGE if not self.get_option_value(SearchOptionGridMode) else settings.SOUNDS_PER_PAGE_COMPACT_MODE

        # Clustering
        only_sounds_within_ids = []
        if allow_beta_search_features(self.request):
            cluster_id = self.get_option_value(SearchOptionClusterId)
            if cluster_id > -1:
                only_sounds_within_ids = get_ids_in_cluster(self.get_clustering_data_cache_key(), cluster_id)

        # Facets
        facets = self.facets
        if self.get_option_value(SearchOptionTagsMode):
            facets[settings.SEARCH_SOUNDS_FIELD_TAGS]['limit'] = 50

        # Number of sounds per pack group
        num_sounds_per_pack_group = 1
        if self.get_option_value(SearchOptionDisplayResultsAsPacks):
            # If displaying search results as packs, include 3 sounds per pack group in the results so we can display these sounds as selected sounds in the
            # display_pack templatetag
            num_sounds_per_pack_group = 3

        # Process similar_to parameter to convert it to a list if a vector is passed instead of a sound ID
        similar_to = self.get_option_value(SearchOptionSimilarTo)
        if similar_to != '':
            # If it stars with '[', then we assume this is a serialized vector passed as target for similarity
            if similar_to.startswith('['):
                similar_to = json.loads(similar_to)
            else:
                # Othrwise, we assume it is a sound id and we pass it as integer
                similar_to = int(similar_to)
        else:
            similar_to = None

        return dict(
            textual_query=self.get_option_value(SearchOptionQuery), 
            query_fields=field_weights, 
            query_filter=self.get_filter_string_for_search_engine(include_filters_from_facets=not exclude_facet_filters),
            field_list=['id', 'score'] if not self.get_option_value(SearchOptionMapMode) else ['id', 'score', 'geotag'],
            current_page=self.get_option_value(SearchOptionPage),
            num_sounds=num_sounds if not self.get_option_value(SearchOptionMapMode) else settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,  
            sort=self.get_option_value(SearchOptionSort),
            group_by_pack=self.get_option_value(SearchOptionGroupByPack) or self.get_option_value(SearchOptionDisplayResultsAsPacks), 
            num_sounds_per_pack_group=num_sounds_per_pack_group,
            facets=facets, 
            only_sounds_with_pack=self.get_option_value(SearchOptionDisplayResultsAsPacks), 
            only_sounds_within_ids=only_sounds_within_ids, 
            similar_to=similar_to
        )
    
    def get_url(self, add_filters=None, remove_filters=None):
        """Returns the URL of the search page (or tags page, see below) corresponding to the current parameters loaded in the SearchQueryProcessor.
        This method also ha sparameters to "add_filters" and "remove_filters", which will return the URL to the search page corresponding to the
        current parameters loaded in the SearchQueryProcessor BUT with some filters added or removed.

        Args:
            add_filters (list, optional): List of filters to be added. Each filter should be a string in the format "field:value",
              e.g.: add_filters=["tag:tagname"]. Default is None.
            remove_filters (list, optional): List of filters to be ignored. Each filter should be a string in the format "field:value",
              e.g.: remove_filters=["tag:tagname"]. Default is None.
        """
        # Decide the base url (if in the tags page, we'll use the base URL for tags, otherwise we use the one for the normal search page)
        if self.tags_mode:
            base_url = reverse("tags")
        else:
            base_url = reverse("sounds-search")
        
        # Add query parameters from search options
        parameters_to_add = {}
        for option in self.options.values():
            if option.set_in_request and not option.is_default_value:
                params_for_url = option.as_URL_params()
                if params_for_url is not None:
                    parameters_to_add.update(params_for_url)
        
        # Add filter parameter
        # Also pass extra filters to be added and/or filters to be removed when making the URL
        filter_for_url = self.get_filter_string_for_url(extra_filters=add_filters, ignore_filters=remove_filters)
        if filter_for_url:
            parameters_to_add['f'] = filter_for_url
        encoded_params = urlencode(parameters_to_add)
        if encoded_params:
            return f'{base_url}?{encoded_params}'
        else:
            return base_url

    # Some util methods and properties to access option values more easily

    def get_option_value(self, option_class):
        return self.options[option_class.name].get_value_to_apply()
                
    @property
    def tags_mode(self):
        return self.get_option_value(SearchOptionTagsMode)

    @property
    def map_mode(self):
        return self.get_option_value(SearchOptionMapMode)

    @property
    def grid_mode(self):
        return self.get_option_value(SearchOptionGridMode)

    @property
    def display_as_packs(self):
        return self.get_option_value(SearchOptionDisplayResultsAsPacks)
    
    @property
    def compute_clusters(self):
        return self.get_option_value(SearchOptionComputeClusters)
