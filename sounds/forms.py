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

from django import forms
from django.db.models import Q
from django.forms import ModelForm, Textarea
from sounds.models import License, Flag, Pack, Sound
from utils.forms import TagField, HtmlCleaningCharField
from utils.mail import send_mail_template
from utils.forms import RecaptchaForm
import re

class GeotaggingForm(forms.Form):
    remove_geotag = forms.BooleanField(required=False)
    lat = forms.FloatField(min_value=-90, max_value=90, required=False)
    lon = forms.FloatField(min_value=-180, max_value=180, required=False)
    zoom = forms.IntegerField(min_value=11, error_messages={'min_value': "You should zoom in more until you reach at least zoom 11."}, required=False)

    def clean(self):
        data = self.cleaned_data

        if not data.get('remove_geotag'):
            lat = data.get('lat', False)
            lon = data.get('lon', False)
            zoom = data.get('zoom', False)

            # second clause is to detect when no values were submitted.
            # otherwise doesn't work in the describe workflow
            if (not (lat and lon and zoom)) and (not (not lat and not lon and not zoom)):
                raise forms.ValidationError('There are missing fields or zoom level is not enough.')

        return data


class SoundDescriptionForm(forms.Form):
    name = forms.CharField(max_length=512, min_length=5,
                           widget=forms.TextInput(attrs={'size': 65, 'class':'inputText'}))
    tags = TagField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 2, 'style':'resize: none;'}),
                    help_text="<br>Separate tags with spaces. Join multi-word tags with dashes. For example: field-recording is a popular tag.")
    description = HtmlCleaningCharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 10, 'style':'resize: none;'}))


class RemixForm(forms.Form):
    sources = forms.CharField(min_length=1, widget=forms.widgets.HiddenInput(), required=False)

    def __init__(self, sound, *args, **kwargs):
        self.sound = sound
        super(RemixForm, self).__init__(*args, **kwargs)

    def clean_sources(self):
        sources = re.sub("[^0-9,]", "", self.cleaned_data['sources'])
        sources = re.sub(",+", ",", sources)
        sources = re.sub("^,+", "", sources)
        sources = re.sub(",+$", "", sources)
        if len(sources) > 0:
            sources = set([int(source) for source in sources.split(",")])
        else:
            sources = set()

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
                source = Sound.objects.get(id=id)
                self.sound.sources.remove(source)
                
                # modify remix_group
                
                
                send_mail_template(
                    u'Sound removed as remix source', 'sounds/email_remix_update.txt',
                    {'source': source, 'action': 'removed', 'remix': self.sound},
                    None, source.user.email
                )
            except Sound.DoesNotExist:
                pass
            except Exception, e:
                # Report any other type of exception and fail silently
                print ("Problem removing source from remix or sending mail: %s" \
                     % e)

        for id in new_sources - old_sources: # in new but not in old
            source = Sound.objects.get(id=id)
            self.sound.sources.add(source)
            try:
                send_mail_template(
                    u'Sound added as remix source', 'sounds/email_remix_update.txt',
                    {'source': source, 'action': 'added', 'remix': self.sound},
                    None, source.user.email
                )
            except Exception, e:
                # Report any exception but fail silently
                print ("Problem sending mail about source added to remix: %s" \
                     % e)


        #print "after save", ",".join([str(source.id) for source in self.sound.sources.all()])


class PackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pack):
        return pack.name


class PackForm(forms.Form):
    pack = PackChoiceField(label="Change pack or remove from pack:", queryset=Pack.objects.none(), required=False)
    new_pack = HtmlCleaningCharField(widget=forms.TextInput(attrs={'size': 45}), label="Or fill in the name of a new pack:", required=False, min_length=1)

    def __init__(self, pack_choices, *args, **kwargs):
        super(PackForm, self).__init__(*args, **kwargs)
        self.fields['pack'].queryset = pack_choices.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')

    # Uncomment the following code to not allow duplicate names in packs (if they belong to different users)
    # What has to be unique is the pair username-packname
    '''
    def clean_new_pack(self):
        try:
            Pack.objects.get(name=self.cleaned_data['new_pack'])
            raise forms.ValidationError('This pack name already exists!')
        except Pack.DoesNotExist: #@UndefinedVariable
            return self.cleaned_data['new_pack']
    '''

class PackDescriptionForm(ModelForm):
    
    class Meta:
        model = Pack
        fields = ('description',)
        widgets = {
            'description': Textarea(attrs={'rows': 5, 'cols':60}),
        }

class LicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(is_public=True), required=True, empty_label=None)

    def clean_license(self):
        if self.cleaned_data['license'].abbreviation == "samp+":
            raise forms.ValidationError('We are in the process of slowly removing this license, please choose another one.')
        return self.cleaned_data['license']


class NewLicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(Q(name__startswith='Attribution') | Q(name__startswith='Creative')),
                                     required=True)

class FlagForm(RecaptchaForm):
    email = forms.EmailField(label="Your email", required=True, 
            help_text="Required.", error_messages={'required' : 'Required, please enter your email address.',
            'invalid' : 'Your email address appears to be invalid, please check if it\'s correct.'})
    reason_type = forms.ChoiceField(choices=Flag.REASON_TYPE_CHOICES,required=True , label='Reason type')
    reason = forms.CharField(widget=forms.Textarea)

    def save(self):
        f = Flag()
        f.reason_type = self.cleaned_data['reason_type']
        f.reason = self.cleaned_data['reason']
        return f #sound and user are set in view
