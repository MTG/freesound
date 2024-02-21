import json

from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
import luqum.tree
from luqum.parser import parser
from luqum.pretty import prettify

from clustering.interface import get_ids_in_cluster


class SearchOption(object):
    request = None
    name = 'option'
    label = 'Option'
    help_text = ''
    set_in_request = None
    disabled = False
    value = None
    value_default = None
    search_engine_field_name = None

    def __init__(self, search_query_processor):
        self.search_query_processor = search_query_processor
        self.load_value()

    def __str__(self):
        return f"{self.name}={self.value} ({'in request' if self.set_in_request else 'not in request'}, {'disabled' if self.disabled else 'enabled'})"

    def load_value(self):
        value_from_request = self.value_from_request(self.search_query_processor.request)
        if value_from_request is not None:
            self.set_in_request = True
            self.value = value_from_request
        else:
            self.set_in_request = False
            self.value = self.get_default_value(self.search_query_processor.request)

    def should_be_disabled(self):
        return False
    
    def value_from_request(self, request):
        # Must return None if the option is not passed in the request
        raise NotImplementedError
    
    def get_default_value(self, request):
        return self.value_default
    
    def get_value_for_filter(self):
        return f'{self.get_value()}'

    def get_value_for_url_param(self):
        return f'{self.value}'
    
    def render_as_filter(self):
        if self.search_engine_field_name is not None:
            if self.set_in_request:
                return f'{self.search_engine_field_name}:{self.get_value_for_filter()}'
    
    def get_value(self):
        return self.value
    
    def get_param_for_url(self):
        return {self.query_param_name: self.get_value_for_url_param()}
    
    def is_default_value(self):
        return self.value == self.value_default
    

class SearchOptionBool(SearchOption):
    value_default = False
    query_param_name = None
    only_active_if_not_default = True
    
    def value_from_request(self, request):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return request.GET.get(self.query_param_name) == '1' or request.GET.get(self.query_param_name) == 'on'
            
    def get_value_for_filter(self):
        return '1' if self.get_value() else '0'
    
    def get_value_for_url_param(self):
        return '1' if self.value else '0'
    
    def render_as_filter(self):
        if self.only_active_if_not_default:
            # If only_active_if_not_default is set, only render filter if value is different from the default
            # Otherwise return None and the filter won't be added
            if not self.is_default_value():
                return super().render_as_filter()
        else:
            return super().render_as_filter()


class SearchOptionInt(SearchOption):
    value_default = -1
    query_param_name = None
    
    def value_from_request(self, request):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return int(request.GET.get(self.query_param_name))


class SearchOptionStr(SearchOption):
    value_default = ''
    query_param_name = None
    
    def value_from_request(self, request):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return request.GET.get(self.query_param_name)


class SearchOptionSelect(SearchOption):
    value_default = ''
    options = []
    query_param_name = None
    
    def value_from_request(self, request):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return request.GET.get(self.query_param_name)


class SearchOptionMultipleSelect(SearchOption):
    value_default = []
    options = []
    
    def value_from_request(self, request):
        value = []
        for option in self.options:
            if option[0] in request.GET:
                if request.GET.get(option[0]) == '1' or request.GET.get(option[0]) == 'on':
                    value.append(option[2])
        return value
    
    def get_param_for_url(self):
        # Multiple-select are implemented using several URL params
        value = self.get_value()
        params = {query_option_name: '1' for query_option_name, _, option_name in self.options if option_name in value}
        return params
    
    def get_options_annotated_with_selection(self):
        options = []
        for option in self.options:
            options.append((option[0], option[1], option[2], option[2] in self.get_value()))
        return options
    

class SearchOptionRange(SearchOption):
    value_default = ['*', '*']
    query_param_min = None
    query_param_max = None
    
    def value_from_request(self, request):
        if self.query_param_min is not None and self.query_param_max is not None:
            if self.query_param_min in request.GET or self.query_param_max in request.GET:
                value = self.value_default.copy()
                if self.query_param_min in request.GET:
                    value[0] = str(request.GET[self.query_param_min])
                if self.query_param_max in request.GET:
                    value[1] = str(request.GET[self.query_param_max])
                return value
            
    def get_param_for_url(self):
        # Range is implemented using 2 URL params
        value = self.get_value()
        return {self.query_param_min: value[0], self.query_param_max: value[1]}

    def get_value_for_filter(self):
        return f'[{self.get_value()[0]} TO {self.get_value()[1]}]'

    def get_value_for_url_param(self):
        return f'[{self.value[0]} TO {self.value[1]}]'


# --- Search options for Freesound search page

class SearchOptionQuery(SearchOptionStr):
    name = 'query'
    query_param_name = 'q'

    def should_be_disabled(self):
        return bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo.name))


class SearchOptionSort(SearchOptionSelect):
    name = 'sort_by'
    label = 'Sort by'
    value_default = settings.SEARCH_SOUNDS_SORT_DEFAULT
    options = [(option, option) for option in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB]
    query_param_name = 's'

    def should_be_disabled(self):
        return bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo.name))
    
    def get_default_value(self, request):
        if self.search_query_processor.get_option_value(SearchOptionQuery.name) == '':
            # When making empty queries and no sorting is specified, automatically set sort to "created desc" as
            # relevance score based sorting makes no sense
            return settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST
        return self.value_default


class SearchOptionPage(SearchOptionInt):
    name= 'page'
    query_param_name = 'page'
    value_default = 1

    def get_value(self):
        # Force return 1 in map mode
        if self.search_query_processor.get_option_value(SearchOptionMapMode.name):
            return 1
        return super().get_value()


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

    def get_value(self):
        # Force return True if display_as_packs is enabled, and False if map_mode is enabled
        if self.search_query_processor.has_filter_with_name('grouping_pack'):
            return False
        elif self.search_query_processor.get_option_value(SearchOptionDisplayResultsAsPacks.name):
            return True
        elif self.search_query_processor.get_option_value(SearchOptionMapMode.name):
            return False
        return super().get_value()

    def should_be_disabled(self):
        return self.search_query_processor.has_filter_with_name('grouping_pack') or \
            self.search_query_processor.get_option_value(SearchOptionDisplayResultsAsPacks.name) or \
            self.search_query_processor.get_option_value(SearchOptionMapMode.name)


class SearchOptionDisplayResultsAsPacks(SearchOptionBool):
    name= 'display_as_packs'
    label= 'Display results as packs'
    query_param_name = 'dp'
    help_text= 'Display search results as packs rather than individual sounds'

    def get_value(self):
        # Force return False if a pack filter is active
        if self.search_query_processor.has_filter_with_name('grouping_pack'):
            return False
        return super().get_value()

    def should_be_disabled(self):
        return self.search_query_processor.has_filter_with_name('grouping_pack') or self.search_query_processor.get_option_value(SearchOptionMapMode.name)


class SearchOptionGridMode(SearchOptionBool):
    name= 'grid_mode'
    label= 'Display results in grid'
    query_param_name = 'cm'
    help_text= 'Display search results in a grid so that more sounds are visible per search results page'

    def get_default_value(self, request):
        if request.user.is_authenticated:
            return request.user.profile.use_compact_mode
        return False
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionMapMode.name)


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
    
    def render_as_filter(self):
        # Force render filter True if map_mode is enabled
        return super().render_as_filter() if not self.search_query_processor.get_option_value(SearchOptionMapMode.name) else f'{self.search_engine_field_name}:1'
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionMapMode.name)


class SearchOptionSimilarTo(SearchOptionStr):
    # NOTE: implement this as SearchOptionStr instead of SearchOptionInt so it supports using vectors in format [x0,x1,x2,...,xn]
    name= 'similar_to'
    query_param_name = 'st'


class SearchOptionTagsMode(SearchOptionBool):
    name= 'tags_mode'
    query_param_name = 'tm'


class SearchOptionClusterId(SearchOptionInt):
    name= 'cluster_id'
    query_param_name = 'cid'


class SearchOptionSearchIn(SearchOptionMultipleSelect):
    name = 'search_in'
    label = 'Search in'
    value_default = []
    options = [
        ('a_tag', 'Tags', settings.SEARCH_SOUNDS_FIELD_TAGS),
        ('a_filename', 'Sound name', settings.SEARCH_SOUNDS_FIELD_NAME),
        ('a_description', 'Description', settings.SEARCH_SOUNDS_FIELD_DESCRIPTION),
        ('a_packname', 'Pack name', settings.SEARCH_SOUNDS_FIELD_PACK_NAME),
        ('a_soundid', 'Sound ID', settings.SEARCH_SOUNDS_FIELD_ID),
        ('a_username', 'Username', settings.SEARCH_SOUNDS_FIELD_USER_NAME)
    ]
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value(SearchOptionTagsMode.name) or bool(self.search_query_processor.get_option_value(SearchOptionSimilarTo.name))


class SearchOptionFieldWeights(SearchOptionStr):
    name= 'field_weights'
    query_param_name = 'w'
    value_default = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS

    def value_from_request(self, request):
        """param weights can be used to specify custom field weights with this format 
        w=field_name1:integer_weight1,field_name2:integrer_weight2, eg: w=name:4,tags:1
        ideally, field names should any of those specified in settings.SEARCH_SOUNDS_FIELD_*
        so the search engine can implement ways to translate the "web names" to "search engine"
        names if needed.
        """
        weights_param = request.GET.get(self.query_param_name, None)
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
        
    def get_value_for_url_param(self):
        value_for_url = ''
        for field, weight in self.get_value().items():
            value_for_url += f'{field}:{weight},'
        if value_for_url.endswith(','):
            value_for_url = value_for_url[:-1]
        return value_for_url
    

# --- Search options for Freesound search page

class SearchQueryProcessor(object):
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
        SearchOptionClusterId
    ]
    errors = ''

    def __init__(self, request):
        self.request = request
        
        # Get filter and parse it. Make sure it is iterable (even if it only has one element)
        self.f = request.GET.get('f', '').strip().lstrip()
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

        # Compatibilty with old URLs in which duration/is remix/is geotagged were passed as raw filters
        # If any of these filters are present, we parse them to get their values and modify the request to simulate 
        # the data being passed in the new expected way. We also remove these filters from the f_parsed object.
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

        # Create option objects and load values
        for optionClass in self.avaialable_options:
            option = optionClass(self)
            self.options[option.name] = option

        # Compute disabled property after all properties are initialized as it may depend on other properties
        for option in self.options.values():
            option.disabled = option.should_be_disabled()

        # Get all the filters which are not represented by search options
        self.non_option_filters = self.load_non_option_filters()

    def load_non_option_filters(self):
        non_option_filters = []
        search_engine_field_names_used_in_options = [option.search_engine_field_name for option in self.options.values() if hasattr(option, 'search_engine_field_name')]
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name not in search_engine_field_names_used_in_options:
                    non_option_filters.append((
                        node.name,
                        str(node.expr)
                    ))
        return non_option_filters

    def get_option_value(self, option_name):
        return self.options[option_name].get_value()
    
    def render_filter_for_search_engine(self, include_filters_from_options=True, extra_filters=None, ignore_filters=None):
        # Returns properly formatetd filter string from all options and non-option filters to be used in the search engine
        ff = []
        if include_filters_from_options:
            for option in self.options.values():
                fit = option.render_as_filter()
                if fit is not None:
                    ff.append(fit)
        for non_option_filter in self.non_option_filters:
            ff.append(f'{non_option_filter[0]}:{non_option_filter[1]}')

        # Remove ignored filters (filters to skip need to be properly formatted, e.g. ignore_filters=["tag:tagname"])
        if ignore_filters is not None:
            ff = [f for f in ff if f not in ignore_filters]

        # Add extra filter (filters to add need to be properly formatted, e.g.  extra_filters=["tag:tagname"])
        if extra_filters is not None:
            ff += extra_filters

        return ' '.join(ff)  # TODO: return filters as a list of different filters to send to SOLR in multiple fq parameters (?)
    
    def render_filter_for_url(self, extra_filters=None, ignore_filters=None):
        # Returns properly formatetd filter string for search URLs (e.g. pagintion) which does NOT include filters already represented
        # by search options (it only includes facet filters and other filters that uers might have manually hacked into the URL)
        return self.render_filter_for_search_engine(include_filters_from_options=False, extra_filters=extra_filters, ignore_filters=ignore_filters)
    
    def get_tags_in_filter(self):
        # Get tags taht are being used in filters (this is used later to remove them from the facet and also for tags mode)
        tags_in_filter = []
        for field, value in self.non_option_filters:
            if field == 'tag':
                if value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]  # Remove quotes
                tags_in_filter.append(value)
        return tags_in_filter

    def has_filter_with_name(self, filter_name):
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name == filter_name:
                    return True
        return False
    
    def get_non_option_filters_for_search_results_page(self):
        filters_data = []
        for name, value in self.non_option_filters:
            filter_data = [name, value, self.get_url(remove_filters=[f'{name}:{value}'])]
            if name == 'grouping_pack':
                # There is a special case for the grouping_pack filter in which we only want to display the name of the pack and not the ID
                filter_data[0] = 'pack'
                if value.startswith('"'):
                    filter_data[1] = '"'+ value.split('_')[1]
                else:
                    filter_data[1] = value.split('_')[1]

            filters_data.append(filter_data)
        return filters_data
 
    def as_query_params(self):

        # Filter field weights by "search in" options
        field_weights = self.get_option_value(SearchOptionFieldWeights.name)
        search_in_value = self.get_option_value(SearchOptionSearchIn.name)
        if search_in_value:
            field_weights = {field: weight for field, weight in field_weights.items() if field in search_in_value}
        
        # Number of sounds
        if self.get_option_value(SearchOptionDisplayResultsAsPacks.name):
            # When displaying results as packs, always return the same number regardless of the compact mode setting
            # This because returning a large number of packs makes the search page very slow
            # If we optimize pack search, this should be removed
            num_sounds = settings.SOUNDS_PER_PAGE
        else:
            num_sounds = settings.SOUNDS_PER_PAGE if not self.get_option_value(SearchOptionGridMode.name) else settings.SOUNDS_PER_PAGE_COMPACT_MODE

        # Clustering
        only_sounds_within_ids = []
        if settings.ENABLE_SEARCH_RESULTS_CLUSTERING:
            cluster_id = self.get_option_value(SearchOptionClusterId.name)
            if cluster_id:
                only_sounds_within_ids = get_ids_in_cluster(self.request, cluster_id)

        # Facets
        facets = settings.SEARCH_SOUNDS_DEFAULT_FACETS.copy()  # TODO: Is copy needed here to avoid modiying the default setting?
        if self.get_option_value(SearchOptionTagsMode.name):
            facets[settings.SEARCH_SOUNDS_FIELD_TAGS]['limit'] = 50

        # Number of sounds per pack group
        num_sounds_per_pack_group = 1
        if self.get_option_value(SearchOptionDisplayResultsAsPacks.name):
            # If displaying search results as packs, include 3 sounds per pack group in the results so we can display these sounds as selected sounds in the
            # display_pack templatetag
            num_sounds_per_pack_group = 3

        # Process similar_to parameter to convert it to a list if a vector is passed instead of a sound ID
        similar_to = self.get_option_value(SearchOptionSimilarTo.name)
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
            textual_query=self.get_option_value(SearchOptionQuery.name), 
            query_fields=field_weights, 
            query_filter=self.render_filter_for_search_engine(),
            field_list=['id', 'score'] if not self.get_option_value(SearchOptionMapMode.name) else ['id', 'score', 'geotag'],
            current_page=self.get_option_value(SearchOptionPage.name),
            num_sounds=num_sounds if not self.get_option_value(SearchOptionMapMode.name) else settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,  
            sort=self.get_option_value(SearchOptionSort.name),
            group_by_pack=self.get_option_value(SearchOptionGroupByPack.name) or self.get_option_value(SearchOptionDisplayResultsAsPacks.name), 
            num_sounds_per_pack_group=num_sounds_per_pack_group,
            facets=facets, 
            only_sounds_with_pack=self.get_option_value(SearchOptionDisplayResultsAsPacks.name), 
            only_sounds_within_ids=only_sounds_within_ids, 
            similar_to=similar_to
        )
    
    def get_url(self, add_filters=None, remove_filters=None):
        parameters_to_add = {}
        
        # Add parameters from search options
        for option in self.options.values():
            if option.set_in_request and not option.is_default_value():
                parameters_to_add.update(option.get_param_for_url())
        
        # Add filter parameter
        # Also pass extra filters to be added and/or filters to be removed when making the URL
        filter_for_url = self.render_filter_for_url(extra_filters=add_filters, ignore_filters=remove_filters)
        if filter_for_url:
            parameters_to_add['f'] = filter_for_url
        encoded_params = urlencode(parameters_to_add)
        if encoded_params:
            return f'{reverse("sounds-search")}?{encoded_params}'
        else:
            return f'{reverse("sounds-search")}'    
        
    def contains_active_advanced_search_options(self):
        # Returns true if query has any active options which belong to the "advanced search" panel
        # Also returns true if the query has active undocumented options which are not hidden in the advanced search panel but that
        # are allowed as "power user" options
        non_advanced_search_option_names = [
            SearchOptionQuery.name, 
            SearchOptionSort.name, 
            SearchOptionPage.name, 
            SearchOptionClusterId.name,
            SearchOptionTagsMode.name,
            SearchOptionDisplayResultsAsPacks.name,
            SearchOptionMapMode.name,
            SearchOptionGridMode.name]
        for option in self.options.values():
            if option.name not in non_advanced_search_option_names:
                if option.set_in_request:
                    if not option.is_default_value():
                        return True
        return False

    @property
    def tags_mode(self):
        return self.get_option_value(SearchOptionTagsMode.name)

    @property
    def map_mode(self):
        return self.get_option_value(SearchOptionMapMode.name)

    @property
    def grid_mode(self):
        return self.get_option_value(SearchOptionGridMode.name)

    @property
    def display_as_packs(self):
        return self.get_option_value(SearchOptionDisplayResultsAsPacks.name)     
    
    def print(self):
        # Prints the SearchQueryProcessor object in a somewhat human readable format
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

