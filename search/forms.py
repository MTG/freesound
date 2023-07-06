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

import logging
import django.forms as forms

from django.conf import settings
from pyparsing import ParseException

from utils.search.search_sounds import parse_weights_parameter, parse_query_filter_string, \
    remove_facet_filters, should_use_compact_mode, get_ids_in_cluster


search_logger = logging.getLogger("search")


class SoundSearchForm(forms.Form):
    q = forms.CharField(required=False)  # query
    f = forms.CharField(required=False)  # filter
    s = forms.CharField(required=False)  # sort

    page = forms.CharField(required=False, initial='1')
    w = forms.CharField(required=False)  # weights

    advanced = forms.BooleanField(required=False)
    
    a_packname = forms.BooleanField(required=False)  # Fields -> pack name
    a_filename = forms.BooleanField(required=False)  # Fields -> file name
    a_soundid = forms.BooleanField(required=False)  # Fields -> sound id
    a_username = forms.BooleanField(required=False)  # Fields -> username
    a_tag = forms.BooleanField(required=False)  # Fields -> tags
    a_description = forms.BooleanField(required=False)  # Fields -> description
    
    duration_min = forms.CharField(required=False, initial='0')
    duration_max = forms.CharField(required=False, initial='*')

    g = forms.BooleanField(required=False)  # group by pack
    only_p = forms.BooleanField(required=False)  # only sounds with packs
    only_g = forms.BooleanField(required=False)  # only geotagged sounds
    only_r = forms.BooleanField(required=False)  # only remixed sounds
    
    cluster_id = forms.CharField(required=False)

    cm = forms.BooleanField(required=False)  # compact mode
    

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    def clean_f(self):
        return self.cleaned_data['f'].strip().lstrip()
    
    def clean_page(self):
        try:
            return int(self.cleaned_data.get('page', 1))
        except ValueError:
            return 1
    
    def clean_duration_min(self):
        return self.cleaned_data.get('duration_min', '0')

    def clean_duration_max(self):
        return self.cleaned_data.get('duration_max', '*') 

    def _has_pack_filter(self):
        return "pack:" in self.cleaned_data['f']
    
    def _has_duration_filter(self):
        return "duration:" in self.cleaned_data['f']
    
    def _search_in_options_checked(self):
         # Check if any of the "search in" options is checked
         return self.cleaned_data['a_packname'] or self.cleaned_data['a_filename'] or \
                self.cleaned_data['a_soundid'] or self.cleaned_data['a_username'] or \
                self.cleaned_data['a_tag'] or self.cleaned_data['a_description']
    
    def get_processed_query_params_and_extra_vars(self):
        if not hasattr(self, 'cleaned_data'):
            raise Exception("You must call is_valid() before calling get_processed_query_params_and_extra_vars()")
        
        # Set some initial query params, then post-process them and add new ones
        query_params = {
            'textual_query': self.cleaned_data['q'],
            'sort': self.cleaned_data['s'],
            'current_page': self.cleaned_data['page'],
            'group_by_pack': True if not 'g' in self.data else self.cleaned_data['g'],  # Group by default
            'only_sounds_with_pack': self.cleaned_data['only_p'],
            'num_sounds': settings.SOUNDS_PER_PAGE if not should_use_compact_mode(self.request) else settings.SOUNDS_PER_PAGE_COMPACT_MODE,
            'facets': settings.SEARCH_SOUNDS_DEFAULT_FACETS
        }

        if query_params['textual_query'] == "" and not query_params['sort']:
            # When making empty queries and no sorting is specified, automatically set sort to "created desc" as
            # relevance score based sorting makes no sense
            query_params['sort'] = settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST

        # If the query is filtered by pack, do not collapse sounds of the same pack (makes no sense)
        # If the query is through AJAX (for sources remix editing), do not collapse by pack
        if self._has_pack_filter() or self.request.GET.get("ajax", "") == "1":
            query_params['group_by_pack'] = False

        # If the query is filtered by pack, do not add the "only sounds with pack" filter (makes no sense)
        if self._has_pack_filter():
            query_params['only_sounds_with_pack'] = False

        # If the query is displaying only sounds with pack, also enable group by pack as this is needed to display
        # results as packs
        if query_params['only_sounds_with_pack']:
            query_params['group_by_pack'] = True

        # Process field weights
        if self.cleaned_data['w']:
            # If weights are specified through request param, parse them
            custom_field_weights = parse_weights_parameter(self.cleaned_data['w'])
            if custom_field_weights is not None:
                query_params['query_fields'] = custom_field_weights
        else:
            # If weights are not specified through request param, check if they are specified through advanced search 
            # options, otherwise use the defaults
            if self._search_in_options_checked():
                id_weight = 0
                tag_weight = 0
                description_weight = 0
                username_weight = 0
                pack_tokenized_weight = 0
                original_filename_weight = 0

                # Set the weights of selected checkboxes
                if  self.cleaned_data['a_soundid']:
                    id_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_ID]
                if  self.cleaned_data['a_tag']:
                    tag_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
                if  self.cleaned_data['a_description']:
                    description_weight = \
                        settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION]
                if  self.cleaned_data['a_username']:
                    username_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_USER_NAME]
                if  self.cleaned_data['a_packname']:
                    pack_tokenized_weight = \
                        settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_PACK_NAME]
                if  self.cleaned_data['a_filename']:
                    original_filename_weight = \
                        settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_NAME]
            else:
                # If no weights specified, use defaults
                id_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_ID]
                tag_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
                description_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION]
                username_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_USER_NAME]
                pack_tokenized_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_PACK_NAME]
                original_filename_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_NAME]

            query_params['query_fields'] = {
                settings.SEARCH_SOUNDS_FIELD_ID: id_weight,
                settings.SEARCH_SOUNDS_FIELD_TAGS: tag_weight,
                settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: description_weight,
                settings.SEARCH_SOUNDS_FIELD_USER_NAME: username_weight,
                settings.SEARCH_SOUNDS_FIELD_PACK_NAME: pack_tokenized_weight,
                settings.SEARCH_SOUNDS_FIELD_NAME: original_filename_weight
            }

        # Parse query filter string and remove empty value fields
        # Also compute some things that will be useful later
        parsing_error = False
        try:
            parsed_filters = parse_query_filter_string(self.cleaned_data['f'])
        except ParseException:
            search_logger.error(f"Query filter parsing error. filter: {self.request.GET.get('f', '')}")
            parsed_filters = []
            parsing_error = True
        filter_query = ' '.join([''.join(filter_str) for filter_str in parsed_filters])
        filter_query_non_facets, has_facet_filter = remove_facet_filters(parsed_filters)
        filter_query_link_more_when_grouping_packs = filter_query.replace(' ', '+')
        tags_in_filter = []
        for filter_data in parsed_filters:
            if filter_data[0] == 'tag':
                tags_in_filter.append(filter_data[2])
        query_params['query_filter'] = filter_query

        # If clustering enabled and we are filtering by a specific cluster, add that information in query params
        if settings.ENABLE_SEARCH_RESULTS_CLUSTERING and self.cleaned_data['cluster_id']:
            in_ids = get_ids_in_cluster(self.request, self.cleaned_data['cluster_id'])
        else:
            in_ids = []
        query_params.update({'only_sounds_within_ids': in_ids})

        # If duration_min/max are not specified but a duration filter is present, set the values to those of the filter
        # so the form values match those of the filter
        if self._has_duration_filter():
            for filter_data in parsed_filters:
                if filter_data[0] == 'duration':
                    index_of_to_clause = [e.lower().strip() for e in filter_data].index('to')
                    self.cleaned_data['duration_min'] = filter_data[index_of_to_clause - 1]
                    self.cleaned_data['duration_max'] = filter_data[index_of_to_clause + 1]

        # These variables are not used for querying the sound collection
        # We keep them separated in order to facilitate the distinction between variables used for performing
        # the Solr query and these extra ones needed for rendering the search template page
        extra_vars = {
            'filter_query_link_more_when_grouping_packs': filter_query_link_more_when_grouping_packs,
            'advanced': self.cleaned_data['advanced'],
            'cluster_id': self.cleaned_data['cluster_id'],
            'filter_query_non_facets': filter_query_non_facets,
            'has_facet_filter': has_facet_filter,
            'parsed_filters': parsed_filters,
            'tags_in_filter': tags_in_filter,
            'parsing_error': parsing_error,
            'raw_weights_parameter': self.cleaned_data['w']
        }

        if parsing_error:
            extra_vars['error_text'] = 'There was an error while searching, is your query correct?'

        return query_params, extra_vars
