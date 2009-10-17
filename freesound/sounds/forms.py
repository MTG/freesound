from django import forms
from django.contrib.auth.models import User
from utils.forms import *

class HiddenSelectionForm(forms.Form):
    form_selection = forms.CharField(widget=forms.widgets.HiddenInput)

class GeotaggingForm(HiddenSelectionForm):
    lat = forms.FloatField(min_value=-180, max_value=180)
    lon = forms.FloatField(min_value=-90, max_value=90)
    zoom = forms.IntegerField(min_value=10, error_messages={'min_value': "You should zoom in more"})

class SoundDescriptionForm(HiddenSelectionForm):
    tags = TagField(widget=forms.widgets.TextInput(attrs={"size":40}), help_text="Please join multi-word tags with dashes. For example: field-recording is a popular tag.")
    description = HtmlCleaningCharField(widget=forms.Textarea)