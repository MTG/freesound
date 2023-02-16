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


import re

from captcha.fields import ReCaptchaField
from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms import ModelForm, Textarea, TextInput
from django.core.signing import BadSignature, SignatureExpired

from accounts.forms import html_tags_help_text
from sounds.models import License, Flag, Pack, Sound
from utils.encryption import sign_with_timestamp, unsign_with_timestamp
from utils.forms import TagField, HtmlCleaningCharField
from utils.mail import send_mail_template


class GeotaggingForm(forms.Form):
    remove_geotag = forms.BooleanField(required=False)
    lat = forms.FloatField(min_value=-90, max_value=90, required=False,
                           error_messages={
                               'min_value': 'Latitude must be between -90 and 90.',
                               'max_value': 'Latitude must be between -90 and 90.'
                           })
    lon = forms.FloatField(min_value=-180, max_value=180, required=False,
                           error_messages={
                               'min_value': 'Longitude must be between -180 and 180.',
                               'max_value': 'Longitude must be between -180 and 180.'
                           })
    zoom = forms.IntegerField(min_value=11,
                              error_messages={'min_value': "The zoom value sould be at least 11."},
                              required=False)

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
                           widget=forms.TextInput(attrs={'size': 65, 'class': 'inputText'}))
    is_explicit = forms.BooleanField(required=False)
    tags = TagField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 3}),
                    help_text="<br>Add at least 3 tags, separating them with spaces. Join multi-word tags with dashes. "
                              "For example: <i>field-recording</i> is a popular tag."
                              "<br>Only use letters a-z and numbers 0-9 with no accents or diacritics")
    description = HtmlCleaningCharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}))

    def __init__(self, *args, **kwargs):
        explicit_disable = False
        if 'explicit_disable' in kwargs:
            explicit_disable = kwargs.get('explicit_disable')
            del kwargs['explicit_disable']

        super().__init__(*args, **kwargs)
        # Disable is_explicit field if is already marked
        self.initial['is_explicit'] = explicit_disable
        self.fields['is_explicit'].disabled = explicit_disable


def _remix_form_clean_sources_helper(cleaned_data):
    sources = re.sub("[^0-9,]", "", cleaned_data['sources'])
    sources = re.sub(",+", ",", sources)
    sources = re.sub("^,+", "", sources)
    sources = re.sub(",+$", "", sources)
    if len(sources) > 0:
        sources = {int(source) for source in sources.split(",")}
    else:
        sources = set()
    return sources


class RemixForm(forms.Form):
    sources = forms.CharField(min_length=1, widget=forms.widgets.HiddenInput(), required=False)

    def __init__(self, sound, *args, **kwargs):
        self.sound = sound
        super().__init__(*args, **kwargs)

    def clean_sources(self):
        return _remix_form_clean_sources_helper(self.cleaned_data)

    def save(self):
        new_sources = self.cleaned_data['sources']
        self.sound.set_sources(new_sources)

class PackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pack):
        return pack.name


class PackForm(forms.Form):
    pack = PackChoiceField(label="Change pack or remove from pack:", queryset=Pack.objects.none(), required=False, empty_label="--- No pack ---")
    new_pack = forms.CharField(widget=forms.TextInput(attrs={'size': 45}),
                               label="Or fill in the name of a new pack:", required=False, min_length=5)

    def __init__(self, pack_choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pack'].queryset = pack_choices.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')


def _pack_form_clean_pack_helper(cleaned_data):
    if 'pack' not in cleaned_data or cleaned_data['pack'] == '' or str(cleaned_data['pack']) == BWPackForm.NO_PACK_CHOICE_VALUE:
        # No pack selected
        return None
    elif str(cleaned_data['pack']) == BWPackForm.NEW_PACK_CHOICE_VALUE:
        # We need to return something different than for "no pack option" so we can disambiguate in the clean method
        return False
    try:
        pack = Pack.objects.get(id=cleaned_data['pack'])
    except Pack.DoesNotExist:
        raise forms.ValidationError('The selected pack object does not exist.')   
    return pack


def _pack_form_clean_helper(cleaned_data):
    if 'pack' in cleaned_data and cleaned_data['pack'] is False:
        # This corresponds to the option "new pack"
        if 'new_pack' not in cleaned_data or not cleaned_data['new_pack'].strip():
            raise forms.ValidationError({'new_pack': ["A name is required for creating a new pack."]})
    return cleaned_data


class BWPackForm(forms.Form):

    NO_PACK_CHOICE_VALUE = '-1'
    NEW_PACK_CHOICE_VALUE = '0'

    pack = forms.ChoiceField(label="Select a pack for this sound:", choices=[], required=False)
    new_pack = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Fill in the name for the new pack'}),
                               required=False, min_length=5, label='')

    def __init__(self, pack_choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pack_choices = pack_choices.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')
        self.fields['pack'].choices = [(NO_PACK_CHOICE_VALUE, '--- No pack ---'), (NEW_PACK_CHOICE_VALUE, 'Create a new pack...')] + [(pack.id, pack.name) for pack in pack_choices]
        # The attrs below are used so that some elements of the dropdown are displayed in gray 
        self.fields['pack'].widget.attrs = {'data-grey-items': f'{BWPackForm.NO_PACK_CHOICE_VALUE},{BWPackForm.NEW_PACK_CHOICE_VALUE}'}

    def clean_pack(self):
        return _pack_form_clean_pack_helper(self.cleaned_data)

    def clean(self):
        return _pack_form_clean_helper(self.cleaned_data)


class PackEditForm(ModelForm):
    pack_sounds = forms.CharField(min_length=1,
                                  widget=forms.widgets.HiddenInput(attrs={'id': 'pack_sounds', 'name': 'pack_sounds'}),
                                  required=False)
    description = HtmlCleaningCharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}))

    def clean_pack_sounds(self):
        pack_sounds = re.sub("[^0-9,]", "", self.cleaned_data['pack_sounds'])
        pack_sounds = re.sub(",+", ",", pack_sounds)
        pack_sounds = re.sub("^,+", "", pack_sounds)
        pack_sounds = re.sub(",+$", "", pack_sounds)
        if len(pack_sounds) > 0:
            pack_sounds = {int(sound) for sound in pack_sounds.split(",")}
        else:
            pack_sounds = set()
        return pack_sounds

    def save(self, force_insert=False, force_update=False, commit=True):
        pack = super().save(commit=False)
        affected_packs = list()
        affected_packs.append(pack)
        new_sounds = self.cleaned_data['pack_sounds']
        current_sounds = pack.sounds.all()
        for snd in current_sounds:
            if snd.id not in new_sounds:
                snd.pack = None
                snd.mark_index_dirty(commit=True)
        for snd in new_sounds:
            current_sounds_ids = [s.id for s in current_sounds]
            if snd not in current_sounds_ids:
                sound = Sound.objects.get(id=snd)
                if sound.pack:
                    affected_packs.append(sound.pack)
                sound.pack = pack
                sound.mark_index_dirty(commit=True)
        if commit:
            pack.save()
        for affected_pack in affected_packs:
            affected_pack.process()
        return pack

    class Meta:
        model = Pack
        fields = ('name', 'description',)
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols': 50}),
        }


def _license_form_clean_license_helper(cleaned_data):
    if "3.0" in cleaned_data['license'].name_with_version:
        raise forms.ValidationError('We are in the process of removing 3.0 licences, please choose the 4.0 equivalent.')                         
    return cleaned_data['license']


class LicenseForm(forms.Form):
    license_qs = License.objects.filter(Q(name__startswith='Attribution') | Q(name__startswith='Creative'))
    license = forms.ModelChoiceField(queryset=license_qs, required=True)

    def __init__(self, *args, **kwargs):
        hide_old_license_versions = kwargs.pop('hide_old_license_versions', False)
        super().__init__(*args, **kwargs)
        if hide_old_license_versions:
            new_qs = License.objects.filter(Q(name__startswith='Attribution') | Q(name__startswith='Creative')).exclude(deed_url__contains="3.0")
            self.fields['license'].queryset = new_qs
            self.license_qs = new_qs
        valid_licenses = ', '.join([f'"{name}"' for name in list(self.license_qs.values_list('name', flat=True))])
        self.fields['license'].error_messages.update({'invalid_choice': 'Invalid license. Should be one of %s'
                                                                        % valid_licenses})
    def clean_license(self):
        return _license_form_clean_license_helper(self.cleaned_data)


class FlagForm(forms.Form):
    email = forms.EmailField(label="Your email", required=True, help_text="Required.",
                             error_messages={'required': 'Required, please enter your email address.', 'invalid': 'Your'
                                             ' email address appears to be invalid, please check if it\'s correct.'})
    reason_type = forms.ChoiceField(choices=Flag.REASON_TYPE_CHOICES, required=True, label='Reason type')
    reason = forms.CharField(widget=forms.Textarea)
    recaptcha = ReCaptchaField(label="")

    def save(self):
        f = Flag()
        f.reason_type = self.cleaned_data['reason_type']
        f.reason = self.cleaned_data['reason']
        f.email = self.cleaned_data['email']
        return f


class DeleteSoundForm(forms.Form):
    encrypted_link = forms.CharField(widget=forms.HiddenInput())

    def clean_encrypted_link(self):
        data = self.cleaned_data['encrypted_link']
        if not data:
            raise PermissionDenied
        try:
            sound_id = unsign_with_timestamp(str(self.sound_id), data, max_age=10)
        except SignatureExpired:
            raise forms.ValidationError("Time expired")
        except BadSignature:
            raise PermissionDenied
        sound_id = int(sound_id)
        if sound_id != self.sound_id:
            raise PermissionDenied
        return data

    def __init__(self, *args, **kwargs):
        self.sound_id = int(kwargs.pop('sound_id'))
        encrypted_link = sign_with_timestamp(self.sound_id)
        kwargs['initial'] = {
                'encrypted_link': encrypted_link
                }
        super().__init__(*args, **kwargs)


class SoundCSVDescriptionForm(SoundDescriptionForm, GeotaggingForm, LicenseForm):
    """
    This is the form that we use to validate sound metadata provided via CSV bulk description.
    This form inherits from other existing forms to consolidate all sound description related fields in one single form.
    None of the forms from which SoundCSVDescriptionForm inherits are ModelForms, therefore this form is only intented
    to validate metadata fields passed to it (i.e. does not have save() method).
    The field "pack_name" is added manually because there is no logic that we want to replicate from PackForm.
    NOTE: I'm not sure why the mulitple inheritance works well in this class. I think some of the individual
    classes init methods are not called, it could be that it works because this is used for the CSV description only
    and the potential errors due to using multiple inheritance do not manifest. This should be investigated
    more closely.
    """
    pack_name = forms.CharField(min_length=5, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False  # Make sound name not required

    def clean(self):
        # Overwrite clean method from 'GeotaggingForm' as we don't need to check for all fields present here because an
        # equivalent check is performed when parsing the geotag format "lat, lon, zoom".
        return self.cleaned_data


class BWSoundEditAndDescribeForm(forms.Form):
    license_field_size = 'small'  # Used to show the small license field UI with this form
    file_full_path = None
    name = forms.CharField(max_length=512, min_length=5,
                           widget=forms.TextInput(attrs={'size': 65, 'class': 'inputText'}))
    tags = TagField(
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 3}),
        help_text="Add at least 3 tags, separating them with spaces. Join multi-word tags with dashes. "
                  "For example: <i>field-recording</i> is a popular tag. "
                  "Only use letters a-z and numbers 0-9 with no accents or diacritics. "
                  "Note that you can <b>copy</b> and <b>paste</b> between tag fields.")
    description = HtmlCleaningCharField(
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}),
        help_text="You can add <i>timestamped</i> comments by using a syntax like \"#1:07 nice bird chirp\" in the description. "
                  "This will be rendered with little play button to play the sound at that timestamp. " + html_tags_help_text)
    is_explicit = forms.BooleanField(required=False, label="The sound contains explicit content")
    license_qs = License.objects.filter(Q(name__startswith='Attribution') | Q(name__startswith='Creative'))
    license = forms.ModelChoiceField(queryset=license_qs, required=True, widget=forms.RadioSelect())
    pack = forms.ChoiceField(label="Select a pack for this sound:", choices=[], required=False)
    new_pack = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Fill in the name for the new pack'}),
                               required=False, min_length=5, label='')
    remove_geotag = forms.BooleanField(required=False, label="Remove geotag")
    lat = forms.FloatField(min_value=-90, max_value=90, required=False,
                           error_messages={
                               'min_value': 'Latitude must be between -90 and 90.',
                               'max_value': 'Latitude must be between -90 and 90.'
                           })
    lon = forms.FloatField(min_value=-180, max_value=180, required=False,
                           error_messages={
                               'min_value': 'Longitude must be between -180 and 180.',
                               'max_value': 'Longitude must be between -180 and 180.'
                           })
    zoom = forms.IntegerField(min_value=11,
                              error_messages={'min_value': "The zoom value sould be at least 11."},
                              required=False)
    sources = forms.CharField(min_length=1, widget=forms.widgets.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        self.file_full_path = kwargs.pop('file_full_path', None)
        explicit_disable = kwargs.pop('explicit_disable', False)
        hide_old_license_versions = kwargs.pop('hide_old_license_versions', False)
        user_packs = kwargs.pop('user_packs', False)
        super().__init__(*args, **kwargs)
        self.fields['is_explicit'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['remove_geotag'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['license'].widget.attrs['class'] = 'bw-radio'
        
        # Disable is_explicit field if is already marked
        self.initial['is_explicit'] = explicit_disable
        self.fields['is_explicit'].disabled = explicit_disable

        # Prepare license field
        if hide_old_license_versions:
            new_qs = License.objects.filter(Q(name__startswith='Attribution') | Q(name__startswith='Creative')).exclude(deed_url__contains="3.0")
            self.fields['license'].queryset = new_qs
            self.license_qs = new_qs
        valid_licenses = ', '.join([f'"{name}"' for name in list(self.license_qs.values_list('name', flat=True))])
        self.fields['license'].error_messages.update({'invalid_choice': f'Invalid license. Should be one of {valid_licenses}'})

        # Prepare pack field
        user_packs = user_packs.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')
        self.fields['pack'].choices = [(BWPackForm.NO_PACK_CHOICE_VALUE, '--- No pack ---'), (BWPackForm.NEW_PACK_CHOICE_VALUE, 'Create a new pack...')] + [(pack.id, pack.name) for pack in user_packs]
        # The attrs below are used so that some elements of the dropdown are displayed in gray 
        self.fields['pack'].widget.attrs = {'data-grey-items': f'{BWPackForm.NO_PACK_CHOICE_VALUE},{BWPackForm.NEW_PACK_CHOICE_VALUE}'}

    def clean(self):
        data = self.cleaned_data
        data = _pack_form_clean_helper(self.cleaned_data)
        if not data.get('remove_geotag'):
            lat = data.get('lat', False)
            lon = data.get('lon', False)
            zoom = data.get('zoom', False)
            if (not (lat and lon and zoom)) and (not (not lat and not lon and not zoom)):
                # If at least one of the three fields is present but some are missing (and we're not "removing" 
                # the geotag), then show "required field" errors where appropriate
                validation_errors_dict = {}
                if not lat and 'lat' not in self.errors:
                    validation_errors_dict['lat'] = ['This field is required.']
                if not lon and 'lon' not in self.errors:
                    validation_errors_dict['lon'] = ['This field is required.']
                if not zoom and 'zoom' not in self.errors:
                    validation_errors_dict['zoom'] = ['This field is required.']
                raise forms.ValidationError(validation_errors_dict)
        return data

    def clean_license(self):
        return _license_form_clean_license_helper(self.cleaned_data)

    def clean_sources(self):
        return _remix_form_clean_sources_helper(self.cleaned_data)

    def clean_pack(self):
        return _pack_form_clean_pack_helper(self.cleaned_data)
