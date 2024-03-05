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

from django.conf import settings


class SearchOption(object):
    """Base class to process and hold information about a search option (e.g. a filter or a sort option) of a search query.
    SearchOption objects parse option data from a request object, and are later able to translate such data into a search
    engine filter and/or a request parameter depeding on the type of option. The class is meant to be subclassed to implement
    particular types of search options (e.g. boolean, integer, string, etc.). The SearchOption object can also include logic 
    for determining when a specific option should be enabled or disabled based on the data of the search query (including the
    values of other search options).
    """
    sqp = None  # SearchQueryProcessor object that holds this option object
    value = None  # Value of the option as a valid Python type (e.g. bool, int, str, list, etc.)
    set_in_request = None  # Stores whether or not the option data is present in the search request
    
    def __init__(self, 
                 advanced=True, 
                 label='',
                 help_text='',  
                 search_engine_field_name=None, 
                 query_param_name=None,
                 value_default=None,
                 get_default_value=None,
                 should_be_disabled=None,
                 get_value_to_apply=None):
        """Initialize the SearchOption object. 
        
        Args:
            advanced (bool, optional): Whether this option is part of the advanced search options (defaults to True).
            label (str, optional): Label to be used in the frontend template when displaying the option.
            help_text (str, optional): Help text to be used in the frontend template when displaying the option.
            search_engine_field_name (str, optional): Field name of the search engine index correspoding to this option (can be None).
            query_param_name (str, optional): Name to represent this option in the URL query parameters (can be None).
            value_default (any, optional): Value of the option to be used when not set in the request (as valid Python type). Note that
              this value can be overriden if passing the get_default_value optional parameter.
            get_default_value (function, optional): A function returning the default value (as a valid Python type) that the option should take
              if not set in the request. The function will be passed the SearchOption itself as an argument.
            should_be_disabled (function, optional): Function to determine if the option should be disabled based on the data of the search query.
              The function will be passed the SearchOption itself as an argument.
            get_value_to_apply (function, optional): Function to determine the value to be used when applying the option in the search engine.
              The function will be passed the SearchOption itself as an argument.
        """
        self.advanced = advanced
        self.label = label  
        self.help_text = help_text
        self.search_engine_field_name = search_engine_field_name
        self.query_param_name = query_param_name
        if value_default is not None:
            self.value_default = value_default
        if get_default_value is not None:
            self.get_default_value = get_default_value
        if should_be_disabled is not None:
            self.should_be_disabled = should_be_disabled
        if get_value_to_apply is not None:
            self.get_value_to_apply = get_value_to_apply
    
    def set_search_query_processor(self, sqp):
        """Set the SearchQueryProcessor object that holds this option object. The sqp parameter is a SearchQueryProcessor object 
        that allows SearchOption objects to access the request object and the value of other search options."""
        self.sqp = sqp

    @property
    def request(self):
        """Property to access the request object from the SearchQueryProcessor object in a convenient way."""
        return self.sqp.request

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
            self.value = self.default_value
    
    def get_value_from_request(self):
        """Return the value of the option as a valid Python type (e.g. bool, int, str, list, etc.) based on the data present
        in the search request. Must return None if the option is not passed in the request. This method is expected to be
        implemented in the subclasses of SearchOption."""
        raise NotImplementedError
    
    @property
    def default_value(self):
        """Returns the default value of the search option as a valid Python type (e.g. bool, int, str, list, etc.) using the
        self.get_default_value member passed as an argument to SearchOption or the existing self.value_default property."""
        if hasattr(self, 'get_default_value'):
            return self.get_default_value(self)
        else:
            return self.value_default
    
    @property
    def is_default_value(self):
        """Returns True if the parsed value of the option is the same as the default value, returns False otherwise."""
        return self.value == self.default_value
    
    @property
    def disabled(self):
        """Returns True if the search option is disabled and false otherwise. If the method self.should_be_disabled has been set in 
        the object constructor, then it is used to compute the disabled property. When a search option is disabled, users will not 
        be able to edit their values when redered in the search form. Other than that, the SearchOption is treated as any other 
        option and will be used when computing query params for the search engine."""
        if hasattr(self, 'should_be_disabled'):
            return self.should_be_disabled(self)
        else:
            return False
        
    def format_value(self, value):
        """Returns a string representation of the value passed as argument to be used in search engine parameters or as a URL parameter. 
        This method must be subclassed to implement meaningful conversions from the passed Python-type value to a string.
        """
        raise NotImplementedError

    @property
    def value_to_apply(self):
        """Returns the value of the option to be used when applying the option in the search engine. By default, this method returns
        the same value which is stored after reading the SearchOption value from the request, but some SearchOptions might use this
        method to implement additional logic for computing the value to be used in the search engine (for example, if the actual value
        to be used should change depending on the value of other search options)."""
        if hasattr(self, 'get_value_to_apply'):
            return self.get_value_to_apply(self)
        else:
            return self.value
    
    def as_filter(self):
        """Returns a string to be used as a search engine filter for applying the search option. If this method returns None, then it 
        will not be applied as a filter. The filter will be applied if the option is expected to be applied as a filter (if it has
        self.search_engine_field_name set) and if it is set in the request or the self.value_to_apply is diffrent than the default
        value."""
        if self.search_engine_field_name is not None:
            if self.set_in_request or (self.value_to_apply != self.default_value):
                return f'{self.search_engine_field_name}:{self.format_value(self.value_to_apply)}'
    
    def as_URL_params(self):
        """Returns a dictionary with the URL parameters to be used when rendering the search option in a URL. Most search options
        will be rendered as a single URL parameter, but some subclasses might override this method to implement more complex logic
        using multiple parameters or other types of calculations. If the option should not be rendered in the URL, return None. Note
        that unlike the value we use to send to the search engine, here we want to use the value as it is set in the original request, 
        without including any additiontal post-processing from self.value_to_apply. This is because we want the URL parameters
        generated by a search option to be equivalent to the parameters of that option passed in the original request.
        """
        if self.query_param_name is not None:
            return {self.query_param_name: self.format_value(self.value)}
        
    @property
    def value_formatted(self):
        """Returns the value of the option formatted to be used in search engine parameters or as a URL parameter. This method is
        conveninent in the search frontend templates to set the request value of the option in the search form."""
        return self.format_value(self.value)
    
    def __str__(self):
        return f"{self.label}={self.value}, apply: {self.value_to_apply} ({'in request' if self.set_in_request else 'not in request'}, {'disabled' if self.disabled else 'enabled'})"
    
    def __copy2__(self):
        newone = type(self)()
        newone.__dict__.update(self.__dict__)
        return newone
    

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
        if self.value_to_apply == True:
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
    def __init__(self, choices=[], **kwargs):
        """Args:
            choices (list): List of available choices in the format [(value, label), ...].
        """
        self.choices =choices
        super().__init__(**kwargs)

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

    def __init__(self, choices=[], query_param_name_prefix='', **kwargs):
        """Args:
            choices (list): List of available choices in the format [(value, label), ...].
            query_param_name_prefix (str): Prefix to be used in the URL parameters to represent the multiple choices.
        """
        self.choices = choices
        self.query_param_name_prefix = query_param_name_prefix
        super().__init__(**kwargs)

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

    def __init__(self, query_param_min=None, query_param_max=None, **kwargs):
        """Args:
            query_param_min (str, optional): Name of the URL parameter to represent the minimum value of the range.
            query_param_max (str, optional): Name of the URL parameter to represent the maximum value of the range.
        """
        self.query_param_min = query_param_min
        self.query_param_max = query_param_max
        super().__init__(**kwargs)

    
    def get_value_from_request(self):
        if self.query_param_min is not None and self.query_param_max is not None:
            if self.query_param_min in self.request.GET or self.query_param_max in self.request.GET:
                value = self.value_default.copy()
                if self.query_param_min in self.request.GET:
                    value_from_param = str(self.request.GET[self.query_param_min])
                    if value_from_param:
                        value[0] = value_from_param
                if self.query_param_max in self.request.GET:
                    value_from_param = str(self.request.GET[self.query_param_max])
                    if value_from_param:
                        value[1] = value_from_param
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


class SearchOptionBoolElementInPath(SearchOptionBool):
    """This is a special type of search option which is not passed as a URL parameter but is determined based on the URL path.
    The "element_in_path" is compared with the request path and the value of the option is set to True if the element is present.
    """

    def __init__(self, element_in_path='', **kwargs):
        """Args:
            element_in_path (str): Element to be checked in the request path.
        """
        self.element_in_path = element_in_path
        super().__init__(**kwargs)

    def get_value_from_request(self):
        return self.element_in_path in self.request.path


class SearchOptionFieldWeights(SearchOptionStr):
    """This is a search option for the "field weights" parameter in the search engine. This parameter must be parsed in a particular
    way which requires further customisation of SearchOption object and therefore can't be implemented with another generic
    SearchOptionX class.
    """
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