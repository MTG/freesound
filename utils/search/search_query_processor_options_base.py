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
        if self.query_param_name is not None:
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
    only_active_if_not_default = True
    
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
    
    def render_as_filter(self):
        if self.only_active_if_not_default:
            # If only_active_if_not_default is set, only render filter if value is different from the default
            # Otherwise return None and the filter won't be added
            if not self.is_default_value():
                return super().render_as_filter()
        else:
            return super().render_as_filter()