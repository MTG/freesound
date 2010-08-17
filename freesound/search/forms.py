import django.forms as forms
    
SEARCH_SORT_OPTIONS_WEB = [
        ("Duration (long first)"," duration desc"),
        ("Duration (short first)", "duration asc"),
        ("Date added (newest first)", "created desc"),
        ("Date added (oldest first)", "created asc"),
        ("Downloads (most first)", "num_downloads desc"),
        ("Downloads (least first)", "num_downloads asc"),
        ("Rating (highest first)", "avg_rating desc"),
        ("Rating (lowest first)", "avg_rating asc")
    ]

SEARCH_SORT_OPTIONS_API = [
        ("duration_desc"," duration desc"),
        ("duration_asc", "duration asc"),
        ("created_desc", "created desc"),
        ("created_asc", "created asc"),
        ("downloads_desc", "num_downloads desc"),
        ("downloads_asc", "num_downloads asc"),
        ("rating_desc", "avg_rating desc"),
        ("rating_asc", "avg_rating asc")
    ]

SEARCH_DEFAULT_SORT = "num_downloads desc"

class SoundSearchForm(forms.Form):
    query   = forms.CharField(required=False, label='q')
    page    = forms.IntegerField(required=False, label='p')
    filter  = forms.CharField(required=False, label='f')
    sort    = forms.ChoiceField(required=False, choices=SEARCH_SORT_OPTIONS_WEB, label='s')
    
    def clean_query(self):
        q = self.cleaned_data['query'] 
        return q if q != None else ""  
    
    def clean_filter(self):
        f = self.cleaned_data['filter'] 
        return f if f != None else ""  
            
    def clean_page(self):
        p = self.cleaned_data['page'] 
        return p if p != None or p >= 1 else 1  
    
    def clean_sort(self):
        s = self.cleaned_data['sort'] 
        return s if s != None else SEARCH_DEFAULT_SORT
        
    def __init__(self, sort_options, *args, **kargs):
        super(SoundSearchForm, self).__init__(*args, **kargs)
        self.fields['sort'].choices = sort_options