from django import forms
from django.contrib.auth.models import User
from utils.forms import *
from models import Pack

class GeotaggingForm(forms.Form):
    remove_geotag = forms.BooleanField(required=False)
    lat = forms.FloatField(min_value=-180, max_value=180, required=False)
    lon = forms.FloatField(min_value=-90, max_value=90, required=False)
    zoom = forms.IntegerField(min_value=11, error_messages={'min_value': "You should zoom in more until you reach at least zoom %d"}, required=False)
    
    def clean(self):
        data = self.cleaned_data

        if not data.get('remove_geotag'):
            lat = data.get('lat')
            lon = data.get('lon')
            zoom = data.get('zoom')

            if not (lat and lon and zoom):
                raise forms.ValidationError('Required fields not present.')
        
        return data

class SoundDescriptionForm(forms.Form):
    tags = TagField(widget=forms.widgets.TextInput(attrs={"size":40}), help_text="Please join multi-word tags with dashes. For example: field-recording is a popular tag.")
    description = HtmlCleaningCharField(widget=forms.Textarea)

class PackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pack):
        return pack.name
    
class PackForm(forms.Form):
    pack = PackChoiceField(label="Change pack or remove from pack:", queryset=Pack.objects.none(), required=False)
    new_pack = HtmlCleaningCharField(label="Or fill in the name of a new pack:", required=False, min_length=1)
    
    def __init__(self, pack_choices, *args, **kwargs):
        super(PackForm, self).__init__(*args, **kwargs)
        self.fields['pack'].queryset = pack_choices
    
    def clean_add_to_new_pack(self):
        try:
            Pack.objects.get(name=self.cleaned_data['new_pack'])
            raise forms.ValidationError('This pack name already exists!')
        except Pack.DoesNotExist: #@UndefinedVariable
            return self.cleaned_data['new_pack']
