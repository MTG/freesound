from django import forms
from sounds.models import License, Flag, Pack, Sound
from utils.forms import TagField, HtmlCleaningCharField
import re

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


class RemixForm(forms.Form):
    sources = forms.CharField(min_length=1, widget=forms.widgets.HiddenInput())
    
    def __init__(self, sound, *args, **kwargs):
        self.sound = sound
        super(RemixForm, self).__init__(*args, **kwargs)
    
    def clean_sources(self):
        sources = re.sub("[^0-9,]", "", self.cleaned_data['sources'])
        sources = re.sub(",+", ",", sources)
        sources = re.sub("^,+", "", sources)
        sources = re.sub(",+$", "", sources)
        
        sources = set([int(source) for source in sources.split(",")])
        
        if len(sources) == 0:
            raise forms.ValidationError('You did not specify any sources')
        
        return sources
        
    def save(self):
        #print "before save", ",".join([str(source.id) for source in self.sound.sources.all()])

        new_sources = self.cleaned_data['sources']
        
        old_sources = set(source["id"] for source in self.sound.sources.all().values("id"))
        
        try:
            new_sources.remove(self.sound.id) # stop the universe from collapsing :-D
        except KeyError:
            pass
        
        for id in old_sources - new_sources: # in old but not in new
            try:
                self.sound.sources.remove(Sound.objects.get(id=id))
            except Sound.DoesNotExist:
                pass
             
        for id in new_sources - old_sources: # in new but not in old
            self.sound.sources.add(Sound.objects.get(id=id))

        #print "after save", ",".join([str(source.id) for source in self.sound.sources.all()])
        

class PackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pack):
        return pack.name
    

class PackForm(forms.Form):
    pack = PackChoiceField(label="Change pack or remove from pack:", queryset=Pack.objects.none(), required=False)
    new_pack = HtmlCleaningCharField(label="Or fill in the name of a new pack:", required=False, min_length=1)
    
    def __init__(self, pack_choices, *args, **kwargs):
        super(PackForm, self).__init__(*args, **kwargs)
        self.fields['pack'].queryset = pack_choices
    
    def clean_new_pack(self):
        try:
            Pack.objects.get(name=self.cleaned_data['new_pack'])
            raise forms.ValidationError('This pack name already exists!')
        except Pack.DoesNotExist: #@UndefinedVariable
            return self.cleaned_data['new_pack']


class LicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(is_public=True), required=True, empty_label=None)
    
    def clean_license(self):
        if self.cleaned_data['license'].abbreviation == "samp+":
            raise forms.ValidationError('We are in the process of slowly removing this license, please choose another one.')
        return self.cleaned_data['license']
    

class NewLicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(name__startswith='Attribution'), 
                                     required=True, 
                                     empty_label=None,
                                     widget=forms.RadioSelect(),
                                     label='')
    


class FlagForm(forms.ModelForm):
    email = forms.EmailField(label="Your email")
    class Meta:
        model = Flag
        exclude = ('sound', 'reporting_user', 'created')