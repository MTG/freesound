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
import settings
from urllib import quote

def my_quote(s):
    return quote(s,safe=":[]*+()'")
    
SEARCH_SORT_OPTIONS_WEB = [
        ("Automatic by relevance", "score desc"),
        ("Duration (long first)", "duration desc"),
        ("Duration (short first)", "duration asc"),
        ("Date added (newest first)", "created desc"),
        ("Date added (oldest first)", "created asc"),
        ("Downloads (most first)", "num_downloads desc"),
        ("Downloads (least first)", "num_downloads asc"),
        ("Rating (highest first)", "avg_rating desc"),
        ("Rating (lowest first)", "avg_rating asc")
    ]

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


class SoundSearchForm(forms.Form):
    q    = forms.CharField(required=False, label='query')
    p    = forms.CharField(required=False, label='page')
    f    = forms.CharField(required=False, label='filter')
    s    = forms.CharField(required=False, label='sort')
    
    def clean_q(self):
        q = self.cleaned_data['q'] 
        return q if q != None else ""  
    
    def clean_f(self):
        f = self.cleaned_data['f'] 
        return f if f != None else ""  
            
    def clean_p(self):
        try:
            p = int(self.cleaned_data['p'])
        except:
            return 1 
        return p if p >= 1 else 1
    
    def clean_s(self):
        s = self.cleaned_data['s']
        for option in self.sort_options:
            if option[0] == s:
                return option[1]
        return SEARCH_DEFAULT_SORT
        
    def __init__(self, sort_options, *args, **kargs):
        super(SoundSearchForm, self).__init__(*args, **kargs)
        self.sort_options = sort_options


class SoundSearchFormAPI(forms.Form):
    query           = forms.CharField(required=False, label='query')
    page            = forms.CharField(required=False, label='page')
    filter          = forms.CharField(required=False, label='filter')
    sort            = forms.CharField(required=False, label='sort')
    fields          = forms.CharField(required=False, label='fields')
    page_size       = forms.CharField(required=False, label='page_size')
    group_by_pack   = forms.CharField(required=False, label='group_by_pack')

    def clean_query(self):
        query = self.cleaned_data['query']
        return my_quote(query) if query != None else ""

    def clean_filter(self):
        filter = self.cleaned_data['filter']
        return my_quote(filter) if filter != None else ""

    def clean_page(self):
        try:
            page = int(self.cleaned_data['page'])
        except:
            return 1
        return page if page >= 1 else 1

    def clean_sort(self):
        sort = self.cleaned_data['sort']
        for option in SEARCH_SORT_OPTIONS_API:
            if option[0] == sort:
                sort = option[1]
                self.original_url_sort_value = option[0]
        sort = SEARCH_DEFAULT_SORT
        self.original_url_sort_value = SEARCH_DEFAULT_SORT.split(' ')[0]

        if sort in [option[1] for option in SEARCH_SORT_OPTIONS_API]:
            if sort == "avg_rating desc":
                sort = [sort, "num_ratings desc"]
            elif  sort == "avg_rating asc":
                sort = [sort, "num_ratings asc"]
            else:
                sort = [sort]
        else:
            sort = [SEARCH_DEFAULT_SORT]
        return sort

    def clean_fields(self):
        fields = self.cleaned_data['fields']
        return my_quote(fields) if fields != None else ""

    def clean_group_by_pack(self):
        requested_group_by_pack = self.cleaned_data['group_by_pack']
        group_by_pack = ''
        if requested_group_by_pack:
            group_by_pack = '1'
        return group_by_pack

    def clean_page_size(self):
        requested_paginate_by = self.cleaned_data[settings.REST_FRAMEWORK['PAGINATE_BY_PARAM']] or settings.REST_FRAMEWORK['PAGINATE_BY']
        return min(int(requested_paginate_by), settings.REST_FRAMEWORK['MAX_PAGINATE_BY'])