from django.utils.safestring import mark_safe
import luqum.tree
from luqum.parser import parser
from luqum.pretty import prettify


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
    

class SearchOptionRange(SearchOption):
    search_enginee_field_name = ''
    
    def value_from_request(self, request, f_parsed_iterable):
        for node in f_parsed_iterable:
            if type(node) == luqum.tree.SearchField:
                if node.name == self.search_enginee_field_name:
                    # node.expr is expected to be of type luqum.tree.Range
                    return [str(node.expr.low), str(node.expr.high)]

    def html(self):
        return \
        f'''<div>
            <div class="bw-search__filter-section-name caps text-light-grey between">
                <span>{self.label_name}</span>
            </div>
            <div class="bw-search__filter-tags-list bw-search__filter-range">
                <input id="filter_{self.name}_min" class="bw-search_input-range v-spacing-1" type="text" value="{self.value[0]}"> - <input id="filter_{self.name}_max" class="bw-search_input-range" type="text" value="{self.value[1]}"> <span>seconds</span>
            </div>
        </div>'''
    

class SearchOptionInt(SearchOption):
    value_default = 0
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
                <input id="filter_{self.name}" class="bw-search_input-range v-spacing-1" type="text" value="{self.value}">
            </div>
        </div>'''
    

class SearchOptionBool(SearchOption):
    value_default = False
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

    def html(self):
        return \
        f'''<label class="between w-100 {'opacity-020' if self.disabled else ''}" title="{self.help_text}">
            <div class="bw-search__filter-checkbox bw-checkbox-label">
                <input id="filter_{self.name}" type="checkbox" class="bw-checkbox" {'disabled' if self.disabled else ''}>
            </div>
            <div class="bw-search__filter-name">{self.label}</div>
        </label>'''
    

class SearchOptionDuration(SearchOptionRange):
    name = 'duration'
    label_name = 'Duration'
    search_enginee_field_name = 'duration'
    value_default = ['0', '*']


class SearchOptionIsGeotagged(SearchOptionBool):
    name = 'is_geotagged'
    label = 'Only geotagged sounds'
    search_enginee_field_name = 'is_geotagged'
    help_text= 'Only find sounds that have geolocation information'
    
    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('map_mode')
    

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


class SearchOptionSearchIn(SearchOption):
    value_default = []
    options = [
        ('a_tag', 'Tags'),
        ('a_filename', 'Sound name'),
        ('a_description', 'Description'),
        ('a_packname', 'Pack name'),
        ('a_packname', 'Sound ID'),
        ('a_username', 'username')
    ]
    
    def value_from_request(self, request, f_parsed_iterable):
        value = []
        for option in self.options:
            if option[0] in request.GET:
                if request.GET.get(option[0]) == '1':
                    value.append(option[0])

    def should_be_disabled(self):
        return self.search_query_processor.get_option_value('tags_mode') or self.search_query_processor.get_option_value('similar_to')

    def html(self):
        html = '<ul class="bw-search__filter-value-list no-margins">'
        for option in self.options:
            html += f'''<li class="bw-search__filter-value v-padding-1">
                            <label class="between w-100">
                                <div class="bw-search__filter-checkbox">
                                    <input type="checkbox" class="bw-checkbox" name="{option[0]}  {'checked' if self.value else ''}  {'disabled' if self.disabled else ''}/>
                                </div>
                                <div class="bw-search__filter-name">Sound name</div>
                            </label>
                        </li>'''
        html += '</ul>'
        return html
    

class SearchOptionSimilarTo(SearchOptionInt):
    name= 'similar_to'
    query_param_name = 'similar_to'


class SearchOptionTagsMode(SearchOptionBool):
    name= 'tags_mode'
    query_param_name = 'tm'
    

class SearchQueryProcessor(object):
    request = None
    textual_query = ''
    parsed_filter = []
    facet_filters = []
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
    ]

    def __init__(self, request):
        self.request = request
        self.q = request.GET.get('q', '')
        self.f = request.GET.get('f', '')
        if self.f:
            self.f_parsed = parser.parse(self.f)
        else:
            self.f_parsed = None
        self.s = request.GET.get('s', '')
        
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

    def get_option_value(self, option_name):
        return self.options[option_name].value

    def print(self):
        print('\nSEARCH QUERY')
        print('q=', self.q)
        print('s=', self.s)
        print('f_parsed:')
        print(prettify(self.f_parsed))
        print('options:')
        for option in self.options.values():
            print('-', option)
        print('non_option_filters:')
        for filter in self.non_option_filters:
            print('-', f'{filter[0]}={filter[1]}')
