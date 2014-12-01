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

import django.forms as forms
from django.conf import settings
from urllib import quote, unquote
from django.contrib.sites.models import Site
from exceptions import BadRequestException


class ApiV2ClientForm(forms.Form):
    name          = forms.CharField(label='Application name', widget=forms.TextInput(attrs={'style': 'width:500px'}))
    url           = forms.URLField(label='Application url', widget=forms.TextInput(attrs={'style': 'width:500px'}))
    redirect_uri  = forms.URLField(label='Your application\'s callback URL*', widget=forms.TextInput(attrs={'style': 'width:500px'}))
    description   = forms.CharField(label='Describe your application', widget=forms.Textarea(attrs={'style': 'width:500px'}))
    accepted_tos  = forms.BooleanField(label='',
                                       help_text='Check this box to accept the <a href="/help/tos_api/" target="_blank">terms of use</a> of the Freesound API',
                                       required=True,
                                       error_messages={'required': 'You must accept the terms of use in order to get access to the API.'})


SEARCH_SORT_OPTIONS_API = [
        ("score", "score desc"),
        ("duration_desc", "duration desc"),
        ("duration_asc", "duration asc"),
        ("created_desc", "created desc"),
        ("created_asc", "created asc"),
        ("downloads_desc", "num_downloads desc"),
        ("downloads_asc", "num_downloads asc"),
        ("rating_desc", "avg_rating desc"),
        ("rating_asc", "avg_rating asc")
    ]

SEARCH_DEFAULT_SORT = "score desc"


def my_quote(s):
    # First encode to ut8 to avoid problems with non standard characters
    s = s.encode('utf8')
    return unicode(quote(s,safe=",:[]*+()'"))


class SoundCombinedSearchFormAPI(forms.Form):
    query               = forms.CharField(required=False, label='query')
    page                = forms.CharField(required=False, label='page')
    filter              = forms.CharField(required=False, label='filter')
    sort                = forms.CharField(required=False, label='sort')
    fields              = forms.CharField(required=False, label='fields')
    descriptors         = forms.CharField(required=False, label='descriptors')
    normalized          = forms.CharField(required=False, label='normalized')
    page_size           = forms.CharField(required=False, label='page_size')
    group_by_pack       = forms.CharField(required=False, label='group_by_pack')
    descriptors_filter  = forms.CharField(required=False, label='descriptors_filter')
    target              = forms.CharField(required=False, label='target')

    def clean_query(self):
        query = self.cleaned_data['query']
        if unquote(query).replace('"','').isspace() or unquote(query).replace('"','') == '':
            return ""
        return my_quote(query) if 'query' in self.data else None

    def clean_filter(self):
        filter = self.cleaned_data['filter']
        if 'filter' in self.data and (not filter or filter.isspace()):
            raise BadRequestException('Invalid filter.')
        return my_quote(filter) if 'filter' in self.data else None

    def clean_descriptors(self):
        descriptors = self.cleaned_data['descriptors']
        return my_quote(descriptors) if descriptors != None else ""

    def clean_normalized(self):
        requested_normalized = self.cleaned_data['normalized']
        normalized = ''
        if requested_normalized:
            normalized = '1'
        return normalized

    def clean_page(self):
        try:
            page = int(self.cleaned_data['page'])
        except:
            return 1
        return page

    def clean_sort(self):

        sort_option = None
        for option in SEARCH_SORT_OPTIONS_API:
            if option[0] == str(self.cleaned_data['sort']):
                sort_option = option[1]
                self.original_url_sort_value = option[0]

        if not sort_option:
            sort_option = SEARCH_DEFAULT_SORT
            self.original_url_sort_value = SEARCH_DEFAULT_SORT.split(' ')[0]

        if sort_option == "avg_rating desc":
            sort = [sort_option, "num_ratings desc"]
        elif sort_option == "avg_rating asc":
            sort = [sort_option, "num_ratings asc"]
        else:
            sort = [sort_option]

        return sort

    def clean_fields(self):
        fields = self.cleaned_data['fields']
        return my_quote(fields) if fields != None else ""

    def clean_group_by_pack(self):
        requested_group_by_pack = self.cleaned_data['group_by_pack']
        group_by_pack = ''
        try:
            if int(requested_group_by_pack):
                group_by_pack = '1'
        except:
            pass
        return group_by_pack

    def clean_page_size(self):
        requested_paginate_by = self.cleaned_data[settings.REST_FRAMEWORK['PAGINATE_BY_PARAM']] or settings.REST_FRAMEWORK['PAGINATE_BY']
        try:
            paginate_by = min(int(requested_paginate_by), settings.REST_FRAMEWORK['MAX_PAGINATE_BY'])
        except:
            paginate_by = settings.REST_FRAMEWORK['MAX_PAGINATE_BY']
        return paginate_by

    def clean_descriptors_filter(self):
        descriptors_filter = self.cleaned_data['descriptors_filter']
        if 'descriptors_filter' in self.data and (not descriptors_filter or descriptors_filter.isspace()):
            raise BadRequestException('Invalid descriptiors_filter.')
        return my_quote(descriptors_filter) if descriptors_filter != None else ""

    def clean_target(self):
        target = self.cleaned_data['target']
        if 'target' in self.data and (not target or target.isspace()):
            raise BadRequestException('Invalid target.')
        return my_quote(target) if target != None else ""

    def construct_link(self, base_url, page=None, filter=None, group_by_pack=None, include_page=True):
        link = "?"
        if self.cleaned_data['query'] != None:
            link += '&query=%s' % self.cleaned_data['query']
        if not filter:
            if self.cleaned_data['filter']:
                link += '&filter=%s' % self.cleaned_data['filter']
        else:
            link += '&filter=%s' % my_quote(filter)
        if self.original_url_sort_value and not self.original_url_sort_value == SEARCH_DEFAULT_SORT.split(' ')[0]:
            link += '&sort=%s' % self.original_url_sort_value
        if self.cleaned_data['descriptors_filter']:
                link += '&descriptors_filter=%s' % self.cleaned_data['descriptors_filter']
        if self.cleaned_data['target']:
                link += '&target=%s' % self.cleaned_data['target']
        if include_page:
            if not page:
                if self.cleaned_data['page'] and self.cleaned_data['page'] != 1:
                    link += '&page=%s' % self.cleaned_data['page']
            else:
                link += '&page=%s' % str(page)
        if self.cleaned_data['page_size'] and not self.cleaned_data['page_size'] == settings.REST_FRAMEWORK['PAGINATE_BY']:
            link += '&page_size=%s' % str(self.cleaned_data['page_size'])
        if self.cleaned_data['fields']:
            link += '&fields=%s' % self.cleaned_data['fields']
        if self.cleaned_data['descriptors']:
            link += '&descriptors=%s' % self.cleaned_data['descriptors']
        if self.cleaned_data['normalized']:
            link += '&normalized=%s' % self.cleaned_data['normalized']
        if not group_by_pack:
            if self.cleaned_data['group_by_pack']:
                link += '&group_by_pack=%s' % self.cleaned_data['group_by_pack']
        else:
            link += '&group_by_pack=%s' % group_by_pack

        return "http://%s%s%s" % (Site.objects.get_current().domain, base_url, link)


class SoundTextSearchFormAPI(SoundCombinedSearchFormAPI):
    '''
    This form is like CombinedSearch but disabling content-search-only fields
    '''

    def clean_target(self):
        return None

    def clean_descriptors_filter(self):
        return None


class SoundContentSearchFormAPI(SoundCombinedSearchFormAPI):
    '''
    This form is like CombinedSearch but disabling text-search-only fields
    '''

    def clean_query(self):
        return None

    def clean_filter(self):
        return None

    def clean_sort(self):
        self.original_url_sort_value = False
        return None

    def clean_group_by_pack(self):
        return None


class SimilarityFormAPI(SoundCombinedSearchFormAPI):

    def clean_query(self):
        return None

    def clean_filter(self):
        return None

    def clean_sort(self):
        self.original_url_sort_value = None
        return None

    def clean_group_by_pack(self):
        return None

    def clean_target(self):
        return None