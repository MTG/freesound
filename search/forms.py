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
        return settings.SEARCH_SOUNDS_SORT_DEFAULT
        
    def __init__(self, sort_options, *args, **kargs):
        super(SoundSearchForm, self).__init__(*args, **kargs)
        self.sort_options = sort_options