import django.forms as forms
from search.views import SEARCH_SORT_OPTIONS_API

class SoundSearchForm(forms.Form):
    q        = forms.CharField(required=False)
    p        = forms.IntegerField(required=False)
    f        = forms.CharField(required=False)
    s        = forms.ChoiceField(required=False, choices=SEARCH_SORT_OPTIONS_API)