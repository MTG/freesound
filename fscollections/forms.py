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
from django.conf import settings
from django import forms
from django.forms import ModelForm, Textarea, TextInput, SelectMultiple
from django.contrib.auth.models import User
from fscollections.models import Collection, CollectionSound
from utils.forms import HtmlCleaningCharField

from sounds.models import Sound

class SelectCollectionOrNewCollectionForm(forms.Form):
    """This form unfolds all the available collections for the user in a modal and allows to select one.
    So far it is only used to add one sound to a collection interacting from the sound player (as previously done
    in Bookmarks). Available collections are those where the user is either the owner or a maintainer, with a number
    of sounds lower than MAX_SOUNDS_PER_COLLECTION and still do not contain the selected sound. New collections can be
    created with a custom name, or with the default name for the personal collection's name (Bookmark), if the user has
    not created any collection yet.

    Args:
        forms (Form): django Form class.

    Raises:
        forms.ValidationError: sound does not exist.
        forms.ValidationError: collection.num_sounds exceeds settings.MAX_SOUNDS_PER_COLLECTION.
        forms.ValidationError: user is not owner nor maintainer so lacks permission to edit the collection.
        forms.ValidationError: sound already exists in collection.
        forms.ValidationError: collection does not exist.
        forms.ValidationError: new collection name already exists in user's collection.
        forms.ValidationError: new collection name is empty
        forms.ValidationError: invalid selected category value

    Returns:
        save: returns the selected collection object to be used
    """

    collection = forms.ChoiceField(
        label=False,
        choices=[], 
        required=True)
    
    new_collection_name = forms.CharField(
        label = False,
        help_text=None,
        max_length = 128,
        required = False)
    
    use_last_collection = forms.BooleanField(widget=forms.HiddenInput(), required=False, initial=False)
    user_collections = None
    user_available_collections = None
    user_full_collections = None

    BOOKMARK_COLLECTION_CHOICE_VALUE = '-1'
    NEW_COLLECTION_CHOICE_VALUE = '0'


    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop('user_collections', False)
        self.user_saving_sound = kwargs.pop('user_saving_sound', False)
        self.sound_id = kwargs.pop('sound_id', False)

        if self.user_collections:
            # NOTE: as a solution to avoid duplicate sounds in a collection, Collections already containing the sound are not selectable
            # this is also useful to discard adding sounds to collections that are full (max_num_sounds)
            self.user_available_collections = Collection.objects.filter(id__in=self.user_collections).exclude(sounds__id=self.sound_id).exclude(is_default_collection=True).exclude(num_sounds__gte=settings.MAX_SOUNDS_PER_COLLECTION)   
        
        display_bookmark_collection = True
        try:
            # if the user already has a Bookmarks Collection, the default BOOKMARK COLLECTION CHOICE VALUE must be the ID of this collection
            default_collection = Collection.objects.get(user=self.user_saving_sound, is_default_collection=True)
            self.BOOKMARK_COLLECTION_CHOICE_VALUE = default_collection.id
            if CollectionSound.objects.filter(sound=self.sound_id, collection=default_collection).exists():
                # if the Bookmarks Collection already contains the sound, don't display it as an option
                display_bookmark_collection = False
        except Collection.DoesNotExist:
            pass

        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = ([(self.BOOKMARK_COLLECTION_CHOICE_VALUE, 'Bookmarks')] if display_bookmark_collection else []) + \
                                           [(self.NEW_COLLECTION_CHOICE_VALUE, 'Create a new collection...')] + \
                                           ([(collection.id, collection.name) for collection in self.user_available_collections ]
                                            if self.user_available_collections else[])
        
        self.fields['new_collection_name'].widget.attrs['placeholder'] = "Fill in the name for the new collection"
        self.fields['collection'].widget.attrs = {
            'data-grey-items': f'{self.BOOKMARK_COLLECTION_CHOICE_VALUE},{self.NEW_COLLECTION_CHOICE_VALUE}'}
    
    def save(self, *args, **kwargs):
        collection_to_use = None

        if not self.cleaned_data['use_last_collection']:
            if self.cleaned_data['collection'] == self.BOOKMARK_COLLECTION_CHOICE_VALUE:
                collection_to_use, _ = Collection.objects.get_or_create(name="Bookmarks", user=self.user_saving_sound, is_default_collection=True)
                # TODO: what happens if user has more than one is_default_collection? Shouldn't happen but this needs a RESTRICTION
            elif self.cleaned_data['collection'] == self.NEW_COLLECTION_CHOICE_VALUE:
                if self.cleaned_data['new_collection_name'] != "":
                    collection = \
                        Collection.objects.create(user=self.user_saving_sound, name=self.cleaned_data['new_collection_name'])
                    collection_to_use = collection
            else:
                collection_to_use = Collection.objects.get(id=self.cleaned_data['collection'])
        else:
            try:
                last_user_collection = \
                    Collection.objects.filter(user=self.user_saving_sound).order_by('-created')[0]
                collection_to_use = last_user_collection
            except IndexError:
                pass 

        maintainers_list = list(collection_to_use.maintainers.all().values_list('id', flat=True))
        if self.user_saving_sound==collection_to_use.user:
            collection, _ = Collection.objects.get_or_create(
                name = collection_to_use.name, id=collection_to_use.id)
        elif self.user_saving_sound.id in maintainers_list:
            collection, _ = Collection.objects.get_or_create(
                name = collection_to_use.name, id=collection_to_use.id)
        return collection
    
    def clean(self):
        clean_data = super().clean()
        try:
            sound = Sound.objects.get(id=self.sound_id, moderation_state="OK")
        except Sound.DoesNotExist:
                raise forms.ValidationError('Unexpected errors occured while handling the sound.')
        # existing collection selected
        try:
            if clean_data['collection'] != '0' and clean_data['new_collection_name'] == '':
                if clean_data['collection'] == '-1':
                    pass
                else:
                    try:
                        collection = Collection.objects.get(id=clean_data['collection'])
                        
                        if collection.num_sounds >= settings.MAX_SOUNDS_PER_COLLECTION:
                            raise forms.ValidationError(f"The chosen collection has reached the maximum number of sounds allowed ({settings.MAX_SOUNDS_PER_COLLECTION})")
                        
                        maintainers_list = list(collection.maintainers.all().values_list('id', flat=True))
                        if self.user_saving_sound.id not in maintainers_list  and self.user_saving_sound != collection.user:
                            raise forms.ValidationError('You do not have permission to edit this collection.')
                        
                        collection_sounds = Sound.objects.filter(collections=collection)
                        if sound in collection_sounds:
                            raise forms.ValidationError('This sound already exists in this collection')
                        
                    except Collection.DoesNotExist:
                        raise forms.ValidationError('This collection does not exist.')
            elif clean_data['new_collection_name'] != '':
                if Collection.objects.filter(user=self.user_saving_sound, name=clean_data['new_collection_name']).exists():
                    raise forms.ValidationError('You already have a collection with this name.')
            else:
                raise forms.ValidationError('Please introduce a valid name for the collection.')

        except KeyError:
                raise forms.ValidationError('The chosen collection is not valid.')
        return clean_data
    
class CollectionEditForm(forms.ModelForm):
    collection_sounds = forms.CharField(min_length=1,
                                  widget=forms.widgets.HiddenInput(attrs={'id': 'collection_sounds', 'name': 'collection_sounds'}),
                                  required=False)
    
    maintainers = forms.CharField(min_length=1, 
                                             widget = forms.widgets.HiddenInput(attrs={'id':'maintainers'}),
                                             required=False)

    def __init__(self, *args, **kwargs):
        self.is_owner = kwargs.pop('is_owner', False)
        self.is_maintainer = kwargs.pop('is_maintainer', False)
        super().__init__(*args, **kwargs)
        self.fields['public'].label = "Visibility"
    
        self.fields['collection_sounds'].help_text=f"You have reached the maximum number of sounds available for a collection ({settings.MAX_SOUNDS_PER_COLLECTION}). " \
        "In order to add new sounds, first remove some of the current ones."

        if self.instance.is_default_collection:
            self.fields['name'].disabled = True
            self.fields['name'].help_text = "Your personal bookmarks collection's name can't be edited."
            self.fields['public'].disabled = True
            self.fields['public'].help_text = "Your personal bookmarks collection is private."
        
        if not self.is_owner and not self.is_maintainer:
            for field in self.fields:
                self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_owner and not self.is_maintainer:
            self.add_error(field=None, error=forms.ValidationError("You don't have permissions to edit this collection"))
        else: 
            if cleaned_data['name'] != self.instance.name:
                if Collection.objects.filter(user=self.instance.user, name=cleaned_data['name']).exists():
                    self.add_error('name', forms.ValidationError("You already have a collection with this name"))
                elif cleaned_data['name'].lower() == 'bookmarks' or cleaned_data['name'].lower() == 'bookmark':
                    self.add_error('name', forms.ValidationError("This collection name is booked for your personal default collection. Please choose another one."))
        collection_sounds = self.cleaned_data.get('collection_sounds').split(',')    
        if len(collection_sounds) > settings.MAX_SOUNDS_PER_COLLECTION:
            self.add_error('collection_sounds', forms.ValidationError(f'You have exceeded the maximum number of sounds for a collection ({settings.MAX_SOUNDS_PER_COLLECTION}).'))
            cleaned_data['collection_sounds'] = collection_sounds[:self.instance.num_sounds]
        return cleaned_data

    def clean_ids_field(self, field):
        # this function cleans the sounds and maintainers fields which store temporary changes on the edit URL
        new_field = re.sub("[^0-9,]", "", self.cleaned_data[field])
        new_field = re.sub(",+", ",", new_field)
        new_field = re.sub("^,+", "", new_field)
        new_field = re.sub(",+$", "", new_field)
        if len(new_field) > 0:
            new_field = {int(usr) for usr in new_field.split(",")}
        else:
            new_field = set()
        return new_field
    
    def save(self, user_adding_sound):
        """This method is used to apply the temporary changes from the edit URL to the DB.
        Useful for maintainers and sounds, where several objects are added to the Collection attrs.
        This way, the server side does not change until the Save Collection button is clicked.

        Args:
            user_adding_sound (User): the user modifying the collection

        Returns:
            collection (Collection): the saved collection with proper modficiations
        """
        collection = super().save(commit=False)        
        new_sounds = self.clean_ids_field('collection_sounds')
        current_sounds = list(Sound.objects.filter(collections=collection).values_list('id', flat=True))
        for snd in new_sounds:
            if snd not in current_sounds:
                sound = Sound.objects.get(id=snd)
                CollectionSound.objects.create(user=user_adding_sound, sound=sound, collection=collection, status='OK')
              
            else:
                current_sounds.remove(snd)
        for snd in current_sounds:
            sound = Sound.objects.get(id=snd)
            CollectionSound.objects.get(collection=collection, sound=sound).delete()

        new_maintainers = set(self.clean_ids_field('maintainers'))
        # if the owner of the collection has been added as a maintainer, discard it
        if collection.user.id in new_maintainers:
            new_maintainers.remove(collection.user.id)
        current_maintainers = list(self.instance.maintainers.values_list('id', flat=True))
        for usr in new_maintainers:
            if usr not in current_maintainers:
                maintainer = User.objects.get(id=usr)
                collection.maintainers.add(maintainer)
            else:
                current_maintainers.remove(usr)
        for usr in current_maintainers:
            maintainer = User.objects.get(id=usr)
            collection.maintainers.remove(maintainer)
        collection.save()
        return collection
    
    class Meta():
        model = Collection
        fields = ['name', 'description', 'public']
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols': 50}),
            'public': forms.RadioSelect(choices=[(True, 'Public'), (False, 'Private')], attrs={'class': 'bw-radio'})
        }

class CollectionEditFormAsMaintainer(CollectionEditForm):
    class Meta(CollectionEditForm.Meta):
        fields = CollectionEditForm.Meta.fields + ['collection_sounds'] + ['maintainers']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'collection_sounds':
                self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        # NOTE: to prevent a maintainer from modifying any field from the server-side, the following validation is carried
        # All fields retrieved from the original model Collection (name, description, visibility) are compared to the original instance ones
        # and if any change in these is found, an error is raised. To prevent changes in "maintainers" even though it is included
        # in the form but disabled (to allow the user to view but not to modify the field), the original collection maintainers
        # are retrieved from DB to ensure no changes are applied to this attribute.
        collection_maintainers = list(self.instance.maintainers.values_list('id', flat=True))
        cleaned_data['maintainers'] = (',').join(str(x) for x in collection_maintainers)
        for field in CollectionEditForm.Meta.fields:
            if cleaned_data[field] != getattr(self.instance,field):
                self.add_error(field, forms.ValidationError("You don't have permissions to edit this field"))
        return cleaned_data

class CreateCollectionForm(forms.ModelForm):
    
    user = None   
    class Meta():
        model = Collection
        fields = ('name', 'description')
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols': 50}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = "Fill in the name for the new collection"
        self.fields['description'].widget.attrs['placeholder'] = "Fill in the description for the new collection"

    def clean(self):
        if Collection.objects.filter(user=self.user, name=self.cleaned_data['name']).exists():
            raise forms.ValidationError("You already have a collection with this name")
        return super().clean()

class MaintainerForm(forms.Form):
    # NOTE: this field got autocompleted with the users' email, and setting autocomplete to 'off' did not work
    # from field widget set up, nor from modal html file, nor from javascript handlers, so apparently the 
    # suitable way to trick the browser into not autocompleting the field is giving the 'autocomplete' 
    # attribute the "new-password" value
    maintainer = forms.CharField(
        widget=TextInput(attrs={'placeholder': "Fill in the usernames separated by commas",
                                'autocomplete':'new-password'}),
        label=False, 
        help_text=None, 
        max_length=128, 
        required=False)
    
    collection = None
    
    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection', False)
        super().__init__(*args, **kwargs)
    def clean(self):
        new_maintainers = self.cleaned_data['maintainer'].split(',').replace(" ","")
        for username in new_maintainers:
            try:
                new_maintainer = User.objects.get(username=username)
                if new_maintainer in self.collection.maintainers.all():
                    raise forms.ValidationError("The user is already a maintainer")
                return super().clean()
            except User.DoesNotExist:
                raise forms.ValidationError("The user does not exist")

