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
    """Base class to process and hold information about a search option (e.g. a filter or a sort option) of a search query.
    SearchOption objects parse option data from a request object, and are later able to translate such data into a search
    engine filter and/or a request parameter depeding on the type of option. The class is meant to be subclassed to implement
    particular types of search options (e.g. boolean, integer, string, etc.). The SearchOption object can also include logic 
    for determining when a specific option should be enabled or disabled based on the data of the search query (including the
    values of other search options).
    """
    name = 'option'  # Name given to the option to refer to it in the SearchQueryProcessor object
    label = 'Option'  # Label to be used in the frontend template when displaying the option
    help_text = ''  # Help text to be used in the frontend template when displaying the option
    value = None  # Value of the option as a valid Python type (e.g. bool, int, str, list, etc.)
    value_default = None  # Value of the option to be used when not set in the request (as valid Python type)
    set_in_request = None  # Stores whether or not the option data is present in the search request
    search_engine_field_name = None  # Field name of the search engine index correspoding to this option (can be None)
    query_param_name = None  # Name to represent this option in the URL query parameters (can be None)
    search_query_processor = None  # SearchQueryProcessor object that holds this option object

    def __init__(self, search_query_processor):
        """Initialize the SearchOption object. The search_query_processor parameter is a SearchQueryProcessor object that allows
        SearchOption objects to access the request object and the value of other search options.
        """
        self.search_query_processor = search_query_processor
        self.load_value()

    @property
    def request(self):
        """Property to access the request object from the SearchQueryProcessor object in a convenient way."""
        return self.search_query_processor.request

    def load_value(self):
        """Sets the value of the option based on the data present in the request. If the option is not present in the request,
        the default value is used. The set_in_request attribute is also set to True or False depending on whether the option
        is present in the request or not.
        """
        value_from_request = self.get_value_from_request()
        if value_from_request is not None:
            self.set_in_request = True
            self.value = value_from_request
        else:
            self.set_in_request = False
            self.value = self.get_default_value()
    
    def get_value_from_request(self):
        """Return the value of the option as a valid Python type (e.g. bool, int, str, list, etc.) based on the data present
        in the search request. Must return None if the option is not passed in the request. This method is expected to be
        implemented in the subclasses of SearchOption."""
        raise NotImplementedError
    
    def get_default_value(self):
        """Gets the default value of the search option as a valid Python type (e.g. bool, int, str, list, etc.). This method
        can be overridden in subclasses if the logic for computing the default value is more complex than simply returning 
        self.value_default."""
        return self.value_default
    
    @property
    def is_default_value(self):
        """Returns True if the parsed value of the option is the same as the default value, returns False otherwise."""
        return self.value == self.value_default
    
    def should_be_disabled(self):
        """Return True if the option should be disabled based on the data of the search query (including the values of other
        options), returns False otherwise. This method can be overridden in subclasses to implement specific logic for disabling
        the search option (if any). By default, a search option is never disabled."""
        return False
    
    @property
    def disabled(self):
        """Returns True if the search option is disabled and false otherwise. This property uses the value of self.should_be_disabled
        and caches it. When a search option is disabled, users will not be able to edit their values when redered in the search form.
        Other than that, the SearchOption is treated as any other option and will be used when computing query params for the search
        engine."""
        if not hasattr(self, '_disabled'):
            self._disabled = self.should_be_disabled()
        return self._disabled
    
    def format_value(self, value):
        """Returns a string representation of the value passed as argument to be used in search engine parameters or as a URL parameter. 
        This method must be subclassed to implement meaningful conversions from the passed Python-type value to a string.
        """
        raise NotImplementedError

    def get_value_to_apply(self):
        """Returns the value of the option to be used when applying the option in the search engine. By default, this method returns
        the same value which is stored after reading the SearchOption value from the request, but some SearchOptions might use this
        method to implement additional logic for computing the value to be used in the search engine (for example, if the actual value
        to be used should change depending on the value of other search options)."""
        return self.value
    
    def as_filter(self):
        """Returns a string to be used as a search engine filter for applying the search option. If the option should not
        be appleid as a search engine filter or the option is not set in the request, return None."""
        if self.search_engine_field_name is not None:
            if self.set_in_request:
                return f'{self.search_engine_field_name}:{self.format_value(self.get_value_to_apply())}'
    
    def as_URL_params(self):
        """Returns a dictionary with the URL parameters to be used when rendering the search option in a URL. Most search options
        will be rendered as a single URL parameter, but some subclasses might override this method to implement more complex logic
        using multiple parameters or other types of calculations. If the option should not be rendered in the URL, return None. Note
        that unlike the value we use to send to the search engine, here we want to use the value as it is set in the original request, 
        without including any additiontal post-processing from self.get_value_to_apply. This is because we want the URL parameters
        generated by a search option to be equivalent to the parameters of that option passed in the original request.
        """
        if self.query_param_name is not None:
            return {self.query_param_name: self.format_value(self.value)}    
    
    def __str__(self):
        return f"{self.name}={self.value} ({'in request' if self.set_in_request else 'not in request'}, {'disabled' if self.disabled else 'enabled'})"
    

class SearchOptionBool(SearchOption):
    value_default = False
    
    def get_value_from_request(self):
        if self.query_param_name is not None:
            if self.query_param_name in self.request.GET:
                return self.request.GET.get(self.query_param_name) == '1' or self.request.GET.get(self.query_param_name) == 'on'
    
    def format_value(self, value):
        return '1' if value else '0'
    
    def as_filter(self):
        """Boolean search options are only added to the filter if they set to True. In this way, when set to False, we return the 
        whole set of results without filtering by this option, but when the option is set, we filter results by this option. It
        might happen that boolean search options added in the future require a different logic and then we should consider
        updating this class to support a different behavior."""
        if self.value == True:
            return super().as_filter()
        

class SearchOptionInt(SearchOption):
    """SearchOption class to represent integer options.
    """
    value_default = -1
    
    def get_value_from_request(self):
        if self.query_param_name is not None:
            if self.query_param_name in self.request.GET:
                return int(self.request.GET.get(self.query_param_name))
            
    def format_value(self, value):
        return str(value)


class SearchOptionStr(SearchOption):
    """SearchOption class to represent string options.
    """
    value_default = ''

    def get_value_from_request(self):
        if self.query_param_name is not None:
            if self.query_param_name in self.request.GET:
                return self.request.GET.get(self.query_param_name)

    def format_value(self, value):
        return str(value)


class SearchOptionChoice(SearchOptionStr):
    """SearchOption class to represent choice options in which one string option is selected 
    from a list of available choices. Choices must have the format [(value, label), ...], typical from
    Django forms.
    """
    choices = []

    def get_choices_annotated_with_selection(self):
        """Returns the list of available choices annotated with a boolean indicating whether the choice 
        is selected or not. This is useful in search templates.
        """
        choices_annotated = []
        for value, label in self.choices:
            choices_annotated.append((value, label, value == self.value))
        return choices_annotated


class SearchOptionMultipleChoice(SearchOption):
    """SearchOption class to represent choice options in which multiple string options are selected 
    from a list of available choices. Choices must have the format [(value, label), ...], typical from
    Django forms. Multiple choices are expected to be passed in the request as multiple URL parameters
    with a common prefix such as "&{prefix}_{value}=1".
    """
    value_default = []
    choices = []
    query_param_name_prefix = ''

    def get_query_param_name(self, value):
        return f'{self.query_param_name_prefix}_{value}'

    def get_value_from_request(self):
        selected_values = []
        for value, _ in self.choices:
            query_param_name = self.get_query_param_name(value)
            if query_param_name in self.request.GET:
                if self.request.GET.get(query_param_name) == '1' or self.request.GET.get(query_param_name) == 'on':
                    selected_values.append(value)
        return selected_values
    
    def format_value(self, value):
        return "[" + " OR ".join([str(v) for v in value]) + "]"
    
    def get_choices_annotated_with_selection(self):
        """Returns the list of available choices annotated with a boolean indicating whether the choice 
        is selected or not. This is useful in search templates.
        """
        choices_annotated = []
        for value, label in self.choices:
            choices_annotated.append((self.get_query_param_name(value), label, value in self.value))
        return choices_annotated
    
    def as_URL_params(self):
        params = {self.get_query_param_name(value): '1' for value, _ in self.choices if value in self.value}
        return params
    

class SearchOptionRange(SearchOption):
    value_default = ['*', '*']
    query_param_min = None
    query_param_max = None
    
    def get_value_from_request(self):
        if self.query_param_min is not None and self.query_param_max is not None:
            if self.query_param_min in self.request.GET or self.query_param_max in self.request.GET:
                value = self.value_default.copy()
                if self.query_param_min in self.request.GET:
                    value[0] = str(self.request.GET[self.query_param_min])
                if self.query_param_max in self.request.GET:
                    value[1] = str(self.request.GET[self.query_param_max])
                return value
            
    def format_value(self, value):
        return f'[{value[0]} TO {value[1]}]'
    
    def as_URL_params(self):
        return {self.query_param_min: self.value[0], 
                self.query_param_max: self.value[1]}
    
    def as_filter(self):
        """SearchOptionRange search options are only added to the filter if the specified range is not covering all possible 
        fieldd values. The defined self.default_value for a range option is expected to include all results, therefore if the
        value is the same as the default value, we don't need to include this option as a filter. It might happen that range 
        search options added in the future require a different logic and then we should consider updating this class to support
        a different behavior."""
        if not self.is_default_value:
            return super().as_filter()
