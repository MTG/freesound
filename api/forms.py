import django.forms as forms

class ApiKeyForm(forms.Form):
    name          = forms.CharField(label='Application name')
    url           = forms.URLField(label='Application url')
    description   = forms.CharField(label='Describe your application', widget=forms.Textarea)
