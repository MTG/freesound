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
from typing import Any, Optional, Sequence, Type, Union
import django.forms as forms

from django.conf import settings
from django.forms.widgets import Widget
from pyparsing import ParseException

from utils.search.search_sounds import parse_weights_parameter, parse_query_filter_string, \
    remove_facet_filters
from clustering.interface import get_ids_in_cluster


search_logger = logging.getLogger("search")


class FieldWithFormAndFieldNameMixin(object):

    def set_form_and_field_name(self, form, field_name):
        self.form = form
        self.field_name = field_name


class SearchFormBooleanField(FieldWithFormAndFieldNameMixin, forms.BooleanField):

    def __init__(self, *args, **kwargs):
        self.value_if_not_present = kwargs.pop('value_if_not_present', None)
        self.no_hidden_field = kwargs.pop('no_hidden_field', False)
        super().__init__(*args, **kwargs)
        if not self.no_hidden_field:
            self.widget.attrs['class'] = 'bw-checkbox bw-checkbox-add-hidden'
        else:
            self.widget.attrs['class'] = 'bw-checkbox'

    def set_form_and_field_name(self, form, field_name):
        super().set_form_and_field_name(form, field_name)
        if not self.no_hidden_field:
            self.widget.attrs['data-hidden-checkbox-name'] = self.get_hidden_field_name()

    def get_hidden_field_name(self):
        return self.field_name + '-hidden'
        
    def clean(self, value):
        if not self.no_hidden_field:
            if self.get_hidden_field_name() not in self.form.data:
                if callable(self.value_if_not_present):
                    default_value = self.value_if_not_present(self.form)
                else:
                    default_value = self.value_if_not_present
                self.form.data = self.form.data.copy()
                self.form.data[self.field_name] = default_value
                return default_value
            return value
        else:
            return super().clean(value)


class SearchFormBooleanFieldWithFilter(SearchFormBooleanField):

    def __init__(self, *args, **kwargs):
        self.search_engine_filter = kwargs.pop('search_engine_filter', None)
        super().__init__(*args, **kwargs)

    def update_filter_query(self, filter_query):
        if self.search_engine_filter is not None:
            filter_query += f" {self.search_engine_filter}"
        return filter_query


class SearchFormDurationField(FieldWithFormAndFieldNameMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs['class'] = 'bw-search_input-duration v-spacing-1'

class SoundSearchForm(forms.Form):
    # Basic query fields
    q = forms.CharField(required=False)  # query
    s = forms.ChoiceField(required=False, choices=[(option, option) for option in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB])  # sort
    
    # Pagination and display fields
    page = forms.CharField(required=False, initial='1')
    g = SearchFormBooleanField(required=False, value_if_not_present=True)  # group by pack
    cm = SearchFormBooleanField(required=False, 
        value_if_not_present=lambda form: False if form.request.user.is_anonymous else form.request.user.profile.use_compact_mode)  # compact mode
    
    # Search engine weight-related fields
    w = forms.CharField(required=False)  # search engine matching weights
    a_packname = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True)  # Fields -> pack name
    a_filename = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True)  # Fields -> file name
    a_soundid = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True)  # Fields -> sound id
    a_username = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True) # Fields -> username
    a_tag = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True)  # Fields -> tags
    a_description = SearchFormBooleanField(required=False, value_if_not_present=False, no_hidden_field=True)   # Fields -> description

    # Search engine filter-related fields
    f = forms.CharField(required=False)  # raw filter (only used for some filters like pack filter and to allow custom raw filters)
    duration_min = SearchFormDurationField(required=False, initial='0.0')
    duration_max = SearchFormDurationField(required=False, initial='*')
    only_p = SearchFormBooleanField(required=False, value_if_not_present=False)  # only sounds with packs
    only_g = SearchFormBooleanFieldWithFilter(required=False, value_if_not_present=False, search_engine_filter='is_geotagged:1')  # only geotagged sounds
    only_r = SearchFormBooleanFieldWithFilter(required=False, value_if_not_present=False, search_engine_filter='in_remix_group:1')  # only remixed sounds
    
    # Clustering related fields
    cluster_id = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)        
        super().__init__(*args, **kwargs)
        
        # Pass a reference of the form instance to all SearchFormBooleanField fields as this is needed
        # to distinguish between unchecked checkboxes and non-present checkboxes in the form data
        for field in self.fields:
            if hasattr(self.fields[field], 'set_form_and_field_name'):
                self.fields[field].set_form_and_field_name(self, field)
                
    def clean_f(self):
        # Note that f is only used for pack filters or custom raw filters. Most of the filters are set
        # through the different form fields
        return self.cleaned_data['f'].strip().lstrip()
    
    def clean_page(self):
        if not 'page' in self.data:
            self.data = self.data.copy()
            self.data['page'] = self.fields['page'].initial
            return int(self.fields['page'].initial)
        try:
            return int(self.cleaned_data.get('page', self.fields['page'].initial))
        except ValueError:
            return int(self.fields['page'].initial)
    
    def clean_duration_min(self):
        # If no duration_min is provided, set the initial value in the form data
        if not 'duration_min' in self.data:
            self.data = self.data.copy()
            self.data['duration_min'] = self.fields['duration_min'].initial
            return self.fields['duration_min'].initial
        if self.cleaned_data['duration_min'] == '*':
            return self.cleaned_data['duration_min']
        try:
            return str(float(self.cleaned_data['duration_min']))
        except ValueError:
            self.fields['duration_min'].initial

    def clean_duration_max(self):
        # If no duration_max is provided, set the initial value in the form data
        if not 'duration_max' in self.data:
            self.data = self.data.copy()
            self.data['duration_max'] = self.fields['duration_max'].initial
            return self.fields['duration_max'].initial
        if self.cleaned_data['duration_max'] == '*':
            return self.cleaned_data['duration_max']
        try:
            return str(float(self.cleaned_data['duration_max']))
        except ValueError:
            self.fields['duration_max'].initial

    def clean_cm(self):
        # Update user preferences if specified cm is diferent from current user preference
        use_compact_mode = self.cleaned_data['cm']
        if self.request.user.is_authenticated:
            if use_compact_mode != self.request.user.profile.use_compact_mode:
                self.request.user.profile.use_compact_mode = use_compact_mode
                self.request.user.profile.save()
        return use_compact_mode

    def _has_pack_filter(self):
        return "pack:" in self.cleaned_data['f']
    
    def _has_duration_filter(self):
        return float(self.cleaned_data['duration_min']) > 0 \
            or self.cleaned_data['duration_max'] != self.fields['duration_max'].initial
    
    def _search_in_options_checked(self):
         # Check if any of the "search in" options is checked
         return self.cleaned_data['a_packname'] or self.cleaned_data['a_filename'] or \
                self.cleaned_data['a_soundid'] or self.cleaned_data['a_username'] or \
                self.cleaned_data['a_tag'] or self.cleaned_data['a_description']
    
    def contains_active_advanced_search_filters(self):
        if not hasattr(self, 'cleaned_data'):
            raise Exception("You must call is_valid() before calling contains_active_advanced_search_filters()")
        
        using_advanced_search_weights = self.request.GET.get("a_tag", False) \
            or self.request.GET.get("a_filename", False) \
            or self.request.GET.get("a_description", False) \
            or self.request.GET.get("a_packname", False) \
            or self.request.GET.get("a_soundid", False) \
            or self.request.GET.get("a_username", False)
        return using_advanced_search_weights \
            or self.cleaned_data['only_g'] \
            or self.cleaned_data['only_r'] \
            or self._has_duration_filter() 
    
    def get_processed_query_params_and_extra_vars(self):
        if not hasattr(self, 'cleaned_data'):
            raise Exception("You must call is_valid() before calling get_processed_query_params_and_extra_vars()")
        
        # Set some initial query params, then post-process them and add new ones
        query_params = {
            'textual_query': self.cleaned_data['q'],
            'sort': self.cleaned_data['s'],
            'current_page': self.cleaned_data['page'],
            'group_by_pack': self.cleaned_data['g'],
            'only_sounds_with_pack': self.cleaned_data['only_p'],
            'num_sounds': settings.SOUNDS_PER_PAGE if not self.cleaned_data['cm'] else settings.SOUNDS_PER_PAGE_COMPACT_MODE,
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
                if self.cleaned_data['a_soundid']:
                    id_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_ID]
                if self.cleaned_data['a_tag']:
                    tag_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
                if self.cleaned_data['a_description']:
                    description_weight = \
                        settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION]
                if self.cleaned_data['a_username']:
                    username_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_USER_NAME]
                if self.cleaned_data['a_packname']:
                    pack_tokenized_weight = \
                        settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_PACK_NAME]
                if self.cleaned_data['a_filename']:
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

        # Consruct filter query based on form data
        f_param = self.cleaned_data['f']
        for field in self.fields:
            if isinstance(self.fields[field], SearchFormBooleanFieldWithFilter):
                if self.cleaned_data[field]:
                    f_param = self.fields[field].update_filter_query(f_param)
        if self._has_duration_filter():
            # If duration filter is specified, add it to the filter query
            duration_filter = "duration:[{} TO {}]".format(self.cleaned_data['duration_min'],
                                                           self.cleaned_data['duration_max'])
            f_param += f' {duration_filter}'
        
        # Parse query filter string and remove empty value fields
        # Also compute some things that will be useful later
        parsing_error = False
        try:
            parsed_filters = parse_query_filter_string(f_param)
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

        # These variables are not used for querying the sound collection
        # We keep them separated in order to facilitate the distinction between variables used for performing
        # the Solr query and these extra ones needed for rendering the search template page
        extra_vars = {
            'filter_query_link_more_when_grouping_packs': filter_query_link_more_when_grouping_packs,
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
