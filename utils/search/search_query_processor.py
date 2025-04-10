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

from utils.clustering_utilities import get_ids_in_cluster, get_clusters_for_query
from utils.encryption import create_hash
from utils.search.backends.solr555pysolr import Solr555PySolrSearchEngine
from utils.search.search_sounds import allow_beta_search_features
from .search_query_processor_options import SearchOptionStr, SearchOptionChoice, \
    SearchOptionInt, SearchOptionBool, SearchOptionRange, SearchOptionMultipleChoice, \
    SearchOption, SearchOptionBoolElementInPath, SearchOptionFieldWeights, \
    SearchOptionBoolFilterInverted


def _get_value_to_apply_group_by_pack(self):
    # Force return True if display_as_packs is enabled, and False if map_mode is enabled
    if self.sqp.has_filter_with_name('grouping_pack'):
        return False
    elif self.sqp.get_option_value_to_apply('display_as_packs'):
        return True
    elif self.sqp.get_option_value_to_apply('map_mode'):
        return False
    return self.value


class SearchQueryProcessor:
    """The SearchQueryProcessor class is used to parse and process search query information from a request object and
    compute a number of useful items for displaying search information in templates, constructing search URLs, and 
    preparing search options to be passed to the backend search engine.
    """
    request = None
    errors = ''
    option_definitions = [
        ('query', SearchOptionStr, dict(
            advanced=False,
            query_param_name='q',
            should_be_disabled=lambda option: bool(option.sqp.get_option_value_to_apply('similar_to'))
        )),
        ('sort_by', SearchOptionChoice, dict(
            advanced=False,
            query_param_name='s',
            label='Sort',
            choices = [(option, option) for option in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB],
            should_be_disabled = lambda option: bool(option.sqp.get_option_value_to_apply('similar_to')),
            get_default_value = lambda option: settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST if option.sqp.get_option_value_to_apply('query') == '' else settings.SEARCH_SOUNDS_SORT_DEFAULT
        )),
        ('page', SearchOptionInt, dict(
            advanced=False,
            query_param_name='page',
            value_default=1,
            get_value_to_apply = lambda option: 1 if option.sqp.get_option_value_to_apply('map_mode') else option.value
        )),
        ('search_in', SearchOptionMultipleChoice, dict(
            query_param_name_prefix='si',
            label='Search in',
            value_default=[],
            choices = [
                (settings.SEARCH_SOUNDS_FIELD_TAGS, 'Tags'),
                (settings.SEARCH_SOUNDS_FIELD_NAME, 'Sound name'),
                (settings.SEARCH_SOUNDS_FIELD_DESCRIPTION, 'Description'),
                (settings.SEARCH_SOUNDS_FIELD_PACK_NAME, 'Pack name'),
                (settings.SEARCH_SOUNDS_FIELD_ID, 'Sound ID'),
                (settings.SEARCH_SOUNDS_FIELD_USER_NAME, 'Username')],
            should_be_disabled = lambda option: option.sqp.get_option_value_to_apply('tags_mode') or bool(option.sqp.get_option_value_to_apply('similar_to'))
        )),
        ('duration', SearchOptionRange, dict(
            query_param_min='d0',
            query_param_max='d1',
            search_engine_field_name = 'duration',
            label = 'Duration',
            value_default=['0', '*']
        )),
        ('is_geotagged', SearchOptionBool, dict(
            query_param_name='ig',
            search_engine_field_name='is_geotagged',
            label='Only geotagged sounds',
            help_text='Only find sounds that have geolocation information',
            should_be_disabled = lambda option: option.sqp.get_option_value_to_apply('map_mode'),
            get_value_to_apply = lambda option: True if option.sqp.get_option_value_to_apply('map_mode') else option.value
        )),
        ('is_remix', SearchOptionBool, dict(
            query_param_name='r',
            search_engine_field_name='in_remix_group',
            label='Only remix sounds',
            help_text='Only find sounds that are a remix of other sounds or have been remixed'
        )),
        ('group_by_pack', SearchOptionBool, dict(
            query_param_name='g',
            label='Group sounds by pack',
            help_text='Group search results so that multiple sounds of the same pack only represent one item',
            value_default=True,
            get_value_to_apply = _get_value_to_apply_group_by_pack,
            should_be_disabled = lambda option: option.sqp.has_filter_with_name('grouping_pack') or option.sqp.get_option_value_to_apply('display_as_packs') or option.sqp.get_option_value_to_apply('map_mode')
        )),
        ('display_as_packs', SearchOptionBool, dict(
            advanced=False,
            query_param_name='dp',
            label='Display results as packs',
            help_text='Display search results as packs rather than individual sounds',
            get_value_to_apply = lambda option: False if option.sqp.has_filter_with_name('grouping_pack') else option.value,
            should_be_disabled = lambda option: option.sqp.has_filter_with_name('grouping_pack') or option.sqp.get_option_value_to_apply('map_mode')
        )),
        ('grid_mode', SearchOptionBool, dict(
            advanced=False,
            query_param_name='cm',
            label='Display results in grid',
            help_text='Display search results in a grid so that more sounds are visible per search results page',
            get_default_value = lambda option: option.request.user.profile.use_compact_mode if option.request.user.is_authenticated else False,
            should_be_disabled = lambda option: option.sqp.get_option_value_to_apply('map_mode')
        )),
        ('map_mode', SearchOptionBool, dict(
            advanced=False,
            query_param_name='mm',
            label='Display results in map',
            help_text='Display search results in a map'
        )),
        ('tags_mode', SearchOptionBoolElementInPath, dict(
            advanced=False,
            element_in_path='/browse/tags/'
        )),
        ('similar_to', SearchOptionStr, dict(
            query_param_name='st',
            label='Similarity target',
            placeholder='Sound ID'
        )),
        ('compute_clusters', SearchOptionBool, dict(
            query_param_name='cc',
            label='Cluster results by sound similarity'
        )),
        ('cluster_id', SearchOptionInt, dict(
            advanced=False,
            query_param_name='cid',
            get_value_to_apply = lambda option: -1 if not option.sqp.get_option_value_to_apply('compute_clusters') else option.value
        )),
        ('similarity_space', SearchOptionChoice, dict(
            query_param_name='ss',
            label='Similarity space',
            choices = [(option, option) for option in settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS.keys()],
            get_default_value = lambda option: settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER
        )),
        ('field_weights', SearchOptionFieldWeights, dict(
            query_param_name = 'w'
        )),
        ('include_audio_problems', SearchOptionBoolFilterInverted, dict(
            query_param_name='eap',
            search_engine_field_name= 'has_audio_problems',
            label='Exclude sounds with potential audio problems'
        )),
        ('single_event', SearchOptionBool, dict(
            query_param_name='se',
            search_engine_field_name= 'ac_single_event',
            label='Only include "single event" sounds',
        ))        
    ]

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

        # Add extra facets if in beta mode
        if allow_beta_search_features(request):
            self.facets.update(settings.SEARCH_SOUNDS_BETA_FACETS)

        # Iterate over option_definitions and instantiate corresponding SearchOption objectss in a self.options dictionary so we 
        # can easily iterate and access options through self.options attribute. 
        self.options = {}
        for option_name, option_class, option_kwargs in self.option_definitions:
            option = option_class(**option_kwargs)
            self.options[option_name] = option
         
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

        # Make sure that only the "category" or "subcategory" facets are active, as we never show both at the same time. Subcategory facet
        # only makes sense if there is a category filter.
        if self.has_category_filter():
            del self.facets[settings.SEARCH_SOUNDS_FIELD_CATEGORY]
        else:
            del self.facets[settings.SEARCH_SOUNDS_FIELD_SUBCATEGORY]
            
        # Implement compatibility with old URLs in which "duration"/"is remix"/"is geotagged" options were passed as raw filters.
        # If any of these filters are present, we parse them to get their values and modify the request to simulate the data being 
        # passed in the new expected way (through request parameters). If present, we also remove these filters from the f_parsed object.
        values_to_update = {}
        for field_name in [self.options['is_remix'].search_engine_field_name, self.options['is_geotagged'].search_engine_field_name]:        
            for node in self.f_parsed:
                if type(node) == luqum.tree.SearchField:
                    if node.name == field_name:
                        values_to_update[field_name] = str(node.expr) == '1'
                        self.f_parsed = [f for f in self.f_parsed if f != node]

        field_name = self.options['duration'].search_engine_field_name
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name == field_name:
                    # node.expr is expected to be of type luqum.tree.Range
                    values_to_update[field_name] = [str(node.expr.low), str(node.expr.high)]
                    self.f_parsed = [f for f in self.f_parsed if f != node]

        if values_to_update:
            self.request.GET = self.request.GET.copy()
            if self.options['is_remix'].search_engine_field_name in values_to_update:
                self.request.GET[self.options['is_remix'].query_param_name] = '1' if values_to_update[self.options['is_remix'].search_engine_field_name] else '0'
            if self.options['is_geotagged'].search_engine_field_name in values_to_update:
                self.request.GET[self.options['is_geotagged'].query_param_name] = '1' if values_to_update[self.options['is_geotagged'].search_engine_field_name] else '0'
            if self.options['duration'].search_engine_field_name in values_to_update:
                self.request.GET[self.options['duration'].query_param_min] = values_to_update[self.options['duration'].search_engine_field_name][0]
                self.request.GET[self.options['duration'].query_param_max] = values_to_update[self.options['duration'].search_engine_field_name][1]

        # Pass the reference to the SearchQueryProcessor object to all search options, and load the search option values from the request
        for option in self.options.values():
            option.set_search_query_processor(self)
            option.load_value()

        # Some of the filters included in the search query (in f_parsed) might belong to filters which are added by SearchOption objects, but some others might
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
            facet_search_engine_field_names = list(self.facets.keys())
            for non_option_filter in self.non_option_filters:
                should_be_included = True
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
        field is the name of the field, value is the value of the filter, and remove_url is the URL that should be followed to remove the filter from the query.
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

        cluster_id = self.get_option_value_to_apply('cluster_id')
        if cluster_id > -1:
            # If a cluster ID filer is present, we also add it to the list of removable filters
            cluster_results = get_clusters_for_query(self)
            if cluster_results is not None and cluster_results['clusters'] is not None and cluster_id in cluster_results['cluster_ids']:
                cluster_number = cluster_results['cluster_ids'].index(cluster_id) + 1
                filters_data.append(['cluster', f'#{cluster_number}', self.get_url().replace(f'cid={cluster_id}', 'cid=-1')])

        return filters_data
    
    def has_filter_with_name(self, field_name):
        """Returns True if the parsed filter has a filter with the given name.
        """
        for node in self.f_parsed:
            if type(node) == luqum.tree.SearchField:
                if node.name == field_name:
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
            if option.advanced:
                if option.set_in_request:
                    if not option.is_default_value:
                        return True
        return False

    def get_clustering_data_cache_key(self, include_filters_from_facets=False):
        """Generates a cache key used to store clustering results in the cache. Note that the key excludes facet filters
        by default because clusters are computed on the subset of results BEFORE applying the facet filters (this is by
        design to avoid recomputing clusters when changing facets). However, the key can be generated including facets as
        well because in some occasions we want to store clustering-related data which does depend on the facet filters which
        are applied after the main clustering computation.

        Args:
            include_filters_from_facets (bool): If True, the key will include filters from facets as well. Default is False.
              Filters that are included in facets correspond to the facet fields defined in self.facets, which defaults to
              settings.SEARCH_SOUNDS_DEFAULT_FACETS.

        Returns:
            str: Cache key for the clustering data
        """
        query_filter = self.get_filter_string_for_search_engine(include_filters_from_facets=include_filters_from_facets)
        key = f'cluster-results-{self.get_option_value_to_apply("query")}-' + \
              f'{query_filter}-{self.get_option_value_to_apply("sort_by")}-' + \
              f'{self.get_option_value_to_apply("similar_to")}-' + \
              f'{self.get_option_value_to_apply("similarity_space")}-' + \
              f'{self.get_option_value_to_apply("group_by_pack")}'
        return create_hash(key, limit=32)

    def get_textual_description(self):
        """Returns a textual description of the search query, e.g.: "cat (some filters applied)"'
        """
        query_description = ''
        textual_query = self.get_option_value_to_apply('query')
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
        for name, option in self.options.items():
            print('-', name, option)
        if self.non_option_filters:
            print('non_option_filters:')
            for filter in self.non_option_filters:
                print('-', f'{filter[0]}={filter[1]}')
                
    def as_query_params(self, exclude_facet_filters=False):
        """Returns a dictionary with the search options and filters to be used as parameters for the SearchEngine.search_sounds method.
        This method post-processes the data loaded into the SearchQueryProcessor to generate an appropriate query_params dict. Note that
        this method includes some complex logic that takes into account the interaction with some option values to calculate the
        query_params values to be used by the search engine. 

        Args:
            exclude_facet_filters (bool, optional): If True, facet filters will not be used to create the query_params dict. Default is False.
              This is useful as part of the clustering features for which we want to make a query which ignores the facet filters provided in the URL.

        Returns:
            dict: Dictionary with the query parameters to be used by the SearchEngine.search_sounds method.
        """

        # Filter field weights by "search in" options
        field_weights = self.get_option_value_to_apply('field_weights')
        search_in_value = self.get_option_value_to_apply('search_in')
        if search_in_value:
            field_weights = {field: weight for field, weight in field_weights.items() if field in search_in_value}
        
        # Number of sounds
        if self.get_option_value_to_apply('display_as_packs'):
            # When displaying results as packs, always return the same number regardless of the compact mode setting
            # This because returning a large number of packs makes the search page very slow
            # If we optimize pack search, this should be removed
            num_sounds = settings.SOUNDS_PER_PAGE
        else:
            num_sounds = settings.SOUNDS_PER_PAGE if not self.get_option_value_to_apply('grid_mode') else settings.SOUNDS_PER_PAGE_COMPACT_MODE

        # Clustering
        only_sounds_within_ids = []
        if allow_beta_search_features(self.request):
            cluster_id = self.get_option_value_to_apply('cluster_id')
            if cluster_id > -1:
                only_sounds_within_ids = get_ids_in_cluster(self.get_clustering_data_cache_key(), cluster_id)

        # Facets
        facets = self.facets
        if self.get_option_value_to_apply('tags_mode'):
            facets[settings.SEARCH_SOUNDS_FIELD_TAGS]['limit'] = 50

        # Number of sounds per pack group
        num_sounds_per_pack_group = 1
        if self.get_option_value_to_apply('display_as_packs'):
            # If displaying search results as packs, include 3 sounds per pack group in the results so we can display these sounds as selected sounds in the
            # display_pack templatetag
            num_sounds_per_pack_group = 3

        # Process similar_to parameter to convert it to a list if a vector is passed instead of a sound ID
        similar_to = self.get_option_value_to_apply('similar_to')
        if similar_to != '':
            # If it stars with '[', then we assume this is a serialized vector passed as target for similarity
            if similar_to.startswith('['):
                similar_to = json.loads(similar_to)
            else:
                # Otherwise, we assume it is a sound id and we pass it as integer
                similar_to = int(similar_to)
        else:
            similar_to = None

        return dict(
            textual_query=self.get_option_value_to_apply('query'), 
            query_fields=field_weights, 
            query_filter=self.get_filter_string_for_search_engine(include_filters_from_facets=not exclude_facet_filters),
            field_list=['id', 'score'] if not self.get_option_value_to_apply('map_mode') else ['id', 'score', 'geotag'],
            current_page=self.get_option_value_to_apply('page'),
            num_sounds=num_sounds if not self.get_option_value_to_apply('map_mode') else settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,  
            sort=self.get_option_value_to_apply('sort_by'),
            group_by_pack=self.get_option_value_to_apply('group_by_pack') or self.get_option_value_to_apply('display_as_packs'), 
            num_sounds_per_pack_group=num_sounds_per_pack_group,
            facets=facets, 
            only_sounds_with_pack=self.get_option_value_to_apply('display_as_packs'), 
            only_sounds_within_ids=only_sounds_within_ids, 
            similar_to=similar_to,
            similar_to_analyzer=self.get_option_value_to_apply('similarity_space')
        )
    
    def get_url(self, add_filters=None, remove_filters=None):
        """Returns the URL of the search page (or tags page, see below) corresponding to the current parameters loaded in the SearchQueryProcessor.
        This method also has parameters to "add_filters" and "remove_filters", which will return the URL to the search page corresponding to the
        current parameters loaded in the SearchQueryProcessor BUT with some filters added or removed.

        Args:
            add_filters (list, optional): List of filters to be added. Each filter should be a string in the format "field:value",
              e.g.: add_filters=["tag:tagname"]. Default is None.
            remove_filters (list, optional): List of filters to be ignored. Each filter should be a string in the format "field:value",
              e.g.: remove_filters=["tag:tagname"]. Default is None.
        """
        # Decide the base url (if in the tags page, we'll use the base URL for tags, otherwise we use the one for the normal search page)
        if self.get_option_value_to_apply('tags_mode'):
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

    # Some util methods to access option values more easily

    def get_option_value_to_apply(self, option_name):
        option = self.options[option_name]
        return option.value_to_apply

    def tags_mode_active(self):
        return self.options['tags_mode'].value_to_apply
    
    def similar_to_active(self):
        return self.options['similar_to'].value_to_apply

    def compute_clusters_active(self):
        return self.options['compute_clusters'].value_to_apply
    
    def display_as_packs_active(self):
        return self.options['display_as_packs'].value_to_apply
    
    def grid_mode_active(self):
        return self.options['grid_mode'].value_to_apply
    
    def map_mode_active(self):
        return self.options['map_mode'].value_to_apply
    
    def has_category_filter(self):
        return self.has_filter_with_name('category')
    