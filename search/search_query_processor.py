from django.conf import settings
from django.utils.safestring import mark_safe
import luqum.tree
from luqum.parser import parser
from luqum.pretty import prettify

import clustering


class SearchOption(object):
    request = None
    f_parsed = None
    name = 'option'
    label_name = 'Option'
    help_text = ''
    set_in_request = None
    disabled = False
    value = None
    value_default = None
    value_disabled = None

    def __init__(self, search_query_processor):
        self.search_query_processor = search_query_processor
        self.load_value()

    def __str__(self):
        return f"{self.name}={self.value} ({'in request' if self.set_in_request else 'not in request'}, {'disabled' if self.disabled else 'enabled'})"

    def load_value(self):
        value_from_request = self.value_from_request(self.search_query_processor.request, self.search_query_processor.f_parsed_iterable)
        if value_from_request is not None:
            self.set_in_request = True
            self.value = value_from_request
        else:
            self.set_in_request = False
            self.value = self.get_default_value(self.search_query_processor.request, self.search_query_processor.f_parsed_iterable)

    def should_be_disabled(self):
        return False
    
    def value_from_request(self, request, f_parsed_iterable):
        # Must return None if the option is not passed in the request
        raise NotImplementedError
    
    def get_default_value(self, request, f_parsed_iterable):
        return self.value_default
    
    def html(self):
        raise NotImplementedError 
    
    def render(self):
        return mark_safe(self.html())
    
    def render_as_filter(self):
        return None
    
    def get_value(self):
        if self.disabled and self.value_disabled is not None:
            return self.value_disabled
        return self.value
    

class SearchOptionRange(SearchOption):
    value_default = ['*', '*']
    value_disabled = ['*', '*']
    search_enginee_field_name = ''
    
    def value_from_request(self, request, f_parsed_iterable):
        for node in f_parsed_iterable:
            if type(node) == luqum.tree.SearchField:
                if node.name == self.search_enginee_field_name:
                    # node.expr is expected to be of type luqum.tree.Range
                    return [str(node.expr.low), str(node.expr.high)]
                
    def render_as_filter(self):
        return f'{self.search_enginee_field_name}:[{self.get_value()[0]} TO {self.get_value()[1]}]'

    def html(self):
        return \
        f'''<div>
            <div class="bw-search__filter-section-name caps text-light-grey between">
                <span>{self.label_name}</span>
            </div>
            <div class="bw-search__filter-tags-list bw-search__filter-range">
                <input id="filter_{self.name}_min" class="bw-search_input-range v-spacing-1" type="text" value="{self.get_value()[0]}"> - <input id="filter_{self.name}_max" class="bw-search_input-range" type="text" value="{self.get_value()[1]}"> <span>seconds</span>
            </div>
        </div>'''
    

class SearchOptionInt(SearchOption):
    value_default = -1
    value_disabled = -1
    search_enginee_field_name = None
    query_param_name = None
    
    def value_from_request(self, request, f_parsed_iterable):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return int(request.GET.get(self.query_param_name))
        
        if self.search_enginee_field_name is not None:
            for node in f_parsed_iterable:
                if type(node) == luqum.tree.SearchField:
                    if node.name == self.name:
                        return int(node.expr)

    def html(self):
        return \
        f'''<div>
            <div class="bw-search__filter-section-name caps text-light-grey between">
                <span>{self.label_name}</span>
            </div>
            <div class="bw-search__filter-tags-list bw-search__filter-range">
                <input id="filter_{self.name}" class="bw-search_input-range v-spacing-1" type="text" value="{self.get_value()}">
            </div>
        </div>'''
    

class SearchOptionStr(SearchOption):
    value_default = ''
    value_disabled = ''
    search_enginee_field_name = None
    query_param_name = None
    
    def value_from_request(self, request, f_parsed_iterable):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return request.GET.get(self.query_param_name)
        
        if self.search_enginee_field_name is not None:
            for node in f_parsed_iterable:
                if type(node) == luqum.tree.SearchField:
                    if node.name == self.name:
                        return str(node.expr)

    def html(self):
        return \
        f'''<div>
            <div class="bw-search__filter-section-name caps text-light-grey between">
                <span>{self.label_name}</span>
            </div>
            <div class="bw-search__filter-tags-list">
                <input id="filter_{self.name}" class="v-spacing-1" type="text" value="{self.get_value()}">
            </div>
        </div>'''


class SearchOptionBool(SearchOption):
    value_default = False
    value_disabled = False
    search_enginee_field_name = None
    query_param_name = None
    
    def value_from_request(self, request, f_parsed_iterable):
        if self.query_param_name is not None:
            if self.query_param_name in request.GET:
                return request.GET.get(self.query_param_name) == '1'
        
        if self.search_enginee_field_name is not None:
            for node in f_parsed_iterable:
                if type(node) == luqum.tree.SearchField:
                    if node.name == self.name:
                        return str(node.expr) == '1'
                    
    def render_as_filter(self):
        if self.search_enginee_field_name is not None:
            return f'{self.search_enginee_field_name}:{1 if self.get_value() else 0}'

    def html(self):
        return \
        f'''<label class="between w-100 {'opacity-020' if self.disabled else ''}" title="{self.help_text}">
            <div class="bw-search__filter-checkbox bw-checkbox-label">
                <input id="filter_{self.name}" type="checkbox" class="bw-checkbox" {'checked' if self.get_value() else ''} {'disabled' if self.disabled else ''}>
            </div>
            <div class="bw-search__filter-name">{self.label}</div>
        </label>'''


class SearchOptionSearchIn(SearchOption):
    name='search_in'
    value_default = []
    options = [
        ('a_tag', 'Tags', settings.SEARCH_SOUNDS_FIELD_TAGS),
        ('a_filename', 'Sound name', settings.SEARCH_SOUNDS_FIELD_NAME),
        ('a_description', 'Description', settings.SEARCH_SOUNDS_FIELD_DESCRIPTION),
        ('a_packname', 'Pack name', settings.SEARCH_SOUNDS_FIELD_PACK_NAME),
        ('a_soundid', 'Sound ID', settings.SEARCH_SOUNDS_FIELD_ID),
        ('a_username', 'username', settings.SEARCH_SOUNDS_FIELD_USER_NAME)
    ]
    
    def value_from_request(self, request, f_parsed_iterable):
        value = []
        for option in self.options:
            if option[0] in request.GET:
                value.append(option[2])
        return value

    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('tags_mode') or self.search_query_processor.get_option_value('similar_to')

    def html(self):
        html = '<ul class="bw-search__filter-value-list no-margins">'
        for option in self.options:
            html += f'''<li class="bw-search__filter-value v-padding-1">
                            <label class="between w-100">
                                <div class="bw-search__filter-checkbox">
                                    <input type="checkbox" class="bw-checkbox" name="{option[0]}  {'checked' if self.get_value() else ''}  {'disabled' if self.disabled else ''}/>
                                </div>
                                <div class="bw-search__filter-name">Sound name</div>
                            </label>
                        </li>'''
        html += '</ul>'
        return html


class SearchOptionFieldWeights(SearchOptionStr):
    name= 'field_weights'
    query_param_name = 'w'
    value_default = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS

    def value_from_request(self, request, f_parsed_iterable):
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

class SearchOptionDuration(SearchOptionRange):
    name = 'duration'
    label_name = 'Duration'
    search_enginee_field_name = 'duration'
    value_default = ['0', '*']


class SearchOptionIsRemix(SearchOptionBool):
    name= 'is_remix'
    label= 'Only remix sounds'
    search_enginee_field_name = 'in_remix_group'
    help_text=  'Only find sounds that are a remix of other sounds or have been remixed'


class SearchOptionGroupByPack(SearchOptionBool):
    name= 'group_by_pack'
    label= 'Group sounds by pack'
    query_param_name = 'g'
    help_text= 'Group search results so that multiple sounds of the same pack only represent one item'
    value_default = True

    def get_value(self):
        # Force return True if display_as_packs is enabled
        if self.search_query_processor.get_option_value('display_as_packs'):
            return True
        return super().get_value()

    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('display_as_packs') or self.search_query_processor.get_option_value('map_mode')


class SearchOptionDisplayResultsAsPacks(SearchOptionBool):
    name= 'display_as_packs'
    label= 'Display results as packs'
    query_param_name = 'only_p'
    help_text= 'Display search results as packs rather than individual sounds'

    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('map_mode')


class SearchOptionGridMode(SearchOptionBool):
    name= 'grid_mode'
    label= 'Display results in grid'
    query_param_name = 'cm'
    help_text= 'Display search results in a grid so that more sounds are visible per search results page'

    def get_default_value(self, request, f_parsed_iterable):
        if request.user.is_authenticated:
            return request.user.profile.use_compact_mode
        return False
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('map_mode')


class SearchOptionMapMode(SearchOptionBool):
    name= 'map_mode'
    label= 'Display results in map'
    query_param_name = 'mm'
    help_text= 'Display search results in a map'


class SearchOptionIsGeotagged(SearchOptionBool):
    name = 'is_geotagged'
    label = 'Only geotagged sounds'
    search_enginee_field_name = 'is_geotagged'
    help_text= 'Only find sounds that have geolocation information'

    def get_value(self):
        # Force return True if map_mode is enabled
        if self.search_query_processor.get_option_value('map_mode'):
            return True
        return super().get_value()
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('map_mode')


class SearchOptionSimilarTo(SearchOptionInt):
    name= 'similar_to'
    query_param_name = 'similar_to'


class SearchOptionTagsMode(SearchOptionBool):
    name= 'tags_mode'
    query_param_name = 'tm'


class SearchOptionClusterId(SearchOptionInt):
    name= 'cluster_id'
    query_param_name = 'cluster_id'
    

class SearchQueryProcessor(object):
    request = None
    options = {}
    avaialable_options = [
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
    filter_parsing_error = ''

    def __init__(self, request):
        self.request = request

        # Textual query
        self.q = request.GET.get('q', '')
        
        # Filter
        self.f = request.GET.get('f', '').strip().lstrip()
        if self.f:
            try:
                self.f_parsed = parser.parse(self.f)
            except luqum.exceptions.ParseError as e:
                self.filter_parsing_error = str(e)
                self.f_parsed = None
        else:
            self.f_parsed = None
        
        # Sort
        self.s = request.GET.get('s', None)
        if self.q =='' and self.s is None:
            # When making empty queries and no sorting is specified, automatically set sort to "created desc" as
            # relevance score based sorting makes no sense
            self.s = settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST

        # Page
        try:
            self.page = int(request.GET.get("page", 1))
        except ValueError:
            self.page = 1
        
        # Create option objects and load values
        for optionClass in self.avaialable_options:
            option = optionClass(self)
            self.options[option.name] = option

        # Compute disabled property after all properties are initialized as it may depend on other properties
        for option in self.options.values():
            option.disabled = option.should_be_disabled()

        # Get all the filters which are not represented by search options
        self.non_option_filters = self.load_non_option_filters()

    @property
    def f_parsed_iterable(self):
        if self.f_parsed is not None:
            if type(self.f_parsed) == luqum.tree.SearchField:
                return [self.f_parsed]
            else:
                return self.f_parsed.children
        return []

    def load_non_option_filters(self):
        non_option_filters = []
        search_engine_field_names_used_in_options = [option.search_enginee_field_name for option in self.options.values() if hasattr(option, 'search_enginee_field_name')]
        for node in self.f_parsed_iterable:
            if type(node) == luqum.tree.SearchField:
                if node.name not in search_engine_field_names_used_in_options:
                    non_option_filters.append((
                        node.name,
                        str(node.expr)
                    ))
        return non_option_filters

    def print(self):
        print('\nSEARCH QUERY')
        print('q=', self.q)
        print('s=', self.s)
        if not self.filter_parsing_error:
            print('f_parsed:')
            print(prettify(self.f_parsed))
        else:
            print('f_parsed error:')
            print(self.filter_parsing_error)
        print('options:')
        for option in self.options.values():
            print('-', option)
        if self.non_option_filters:
            print('non_option_filters:')
            for filter in self.non_option_filters:
                print('-', f'{filter[0]}={filter[1]}')

    def get_option_value(self, option_name):
        return self.options[option_name].get_value()
    
    def render_filter(self):
        # Returns properly formatetd filter string from all options and non-option filters
        ff = []
        for option in self.options.values():
            fit = option.render_as_filter()
            if fit is not None:
                ff.append(fit)

        for non_option_filter in self.non_option_filters:
            ff.append(f'{non_option_filter[0]}:{non_option_filter[1]}')

        return ' '.join(ff)  # TODO: return filters as a list of different filters to send to SOLR in multiple fq parameters (?)
    
    def get_tags_in_filter(self):
        # Get tags taht are being used in filters (this is used later to remove them from the facet and also for tags mode)
        tags_in_filter = []
        for field, value in self.non_option_filters:
            if field == 'tag':
                if value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]  # Remove quotes
                tags_in_filter.append(value)
        return tags_in_filter
 
    def as_query_params(self):

        # Filter field weights by "search in" options
        field_weights = self.get_option_value('field_weights')
        field_weights = {field: weight for field, weight in field_weights.items() if field in self.get_option_value('field_weights')}
        
        # Number of sounds
        if self.get_option_value('display_as_packs'):
            # When displaying results as packs, always return the same number regardless of the compact mode setting
            # This because returning a large number of packs makes the search page very slow
            # If we optimize pack search, this should be removed
            num_sounds = settings.SOUNDS_PER_PAGE
        else:
            num_sounds = settings.SOUNDS_PER_PAGE if not self.get_option_value('grid_mode') else settings.SOUNDS_PER_PAGE_COMPACT_MODE

        # Clustering
        only_sounds_within_ids = []
        if settings.ENABLE_SEARCH_RESULTS_CLUSTERING:
            cluster_id = self.get_option_value('cluster_id')
            if cluster_id:
                only_sounds_within_ids = clustering.interface.get_ids_in_cluster(self.request, cluster_id)

        # Facets
        facets = settings.SEARCH_SOUNDS_DEFAULT_FACETS.copy()  # TODO: Is copy needed here to avoid modiying the default setting?
        if self.get_option_value('tags_mode'):
            facets[settings.SEARCH_SOUNDS_FIELD_TAGS]['limit'] = 50

        # Number of sounds per pack group
        num_sounds_per_pack_group = 1
        if self.get_option_value('group_by_pack'):
            # If displaying search results as packs, include 3 sounds per pack group in the results so we can display these sounds as selected sounds in the
            # display_pack templatetag
            num_sounds_per_pack_group = 3

        return dict(
            textual_query=self.q, 
            query_fields=field_weights, 
            query_filter=self.render_filter(),
            field_list=['id', 'score'] if not self.get_option_value('map_mode') else ['id', 'score', 'geotag'],
            current_page=self.page if not self.get_option_value('map_mode') else 1, 
            num_sounds=num_sounds if not self.get_option_value('map_mode') else settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,  
            sort=self.s,
            group_by_pack=self.get_option_value('group_by_pack') or self.get_option_value('display_as_packs'), 
            num_sounds_per_pack_group=num_sounds_per_pack_group,
            facets=facets, 
            only_sounds_with_pack=self.get_option_value('display_as_packs'), 
            only_sounds_within_ids=only_sounds_within_ids, 
            similar_to=self.get_option_value('similar_to')
        )
