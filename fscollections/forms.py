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
from django import forms
from django.forms import ModelForm, Textarea, TextInput, SelectMultiple
from django.contrib.auth.models import User
from fscollections.models import Collection, CollectionSound
from utils.forms import HtmlCleaningCharField

from sounds.models import Sound

#this class was aimed to perform similarly to BookmarkSound, however, at first the method to add a sound to a collection
#will be opening the search engine in a modal, looking for a sound in there and adding it to the actual collection page
#this can be found in edit pack -> add sounds
#class CollectSoundForm(forms.ModelForm):

class CollectionSoundForm(forms.Form):
    #list of existing collections 
    #add sound to collection from sound page
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

    BOOKMARK_COLLECTION_CHOICE_VALUE = '-1'
    NEW_COLLECTION_CHOICE_VALUE = '0'


    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop('user_collections', False)
        self.user_saving_sound = kwargs.pop('user_saving_sound', False)
        self.sound_id = kwargs.pop('sound_id', False)

        if self.user_collections:
            # NOTE: as a provisional solution to avoid duplicate sounds in a collection, Collections already containing the sound are not selectable
            self.user_available_collections = Collection.objects.filter(id__in=self.user_collections).exclude(collectionsound__sound__id=self.sound_id).exclude(is_default_collection=True)   
        
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
                        Collection(user=self.user_saving_sound, name=self.cleaned_data['new_collection_name'])
                    collection.save()
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
        # If collection already exists, don't save it and return the existing one
        collection, _ = Collection.objects.get_or_create(
            name = collection_to_use.name, user=self.user_saving_sound)
        return collection
    
    def clean(self):
        collection = self.cleaned_data['collection']
        if CollectionSound.objects.filter(collection=collection,sound=self.sound_id).exists():
            self.add_error('collection', forms.ValidationError("This sound already exists in the collection"))
        return super().clean()
    
class CollectionEditForm(forms.ModelForm):
    collection_sounds = forms.CharField(min_length=1,
                                  widget=forms.widgets.HiddenInput(attrs={'id': 'collection_sounds', 'name': 'collection_sounds'}),
                                  required=False)
    
    collection_maintainers = forms.CharField(min_length=1, 
                                             widget = forms.widgets.HiddenInput(attrs={'id':'collection_maintainers', 'name': 'collection_maintainers'}),
                                             required=False)

    def __init__(self, *args, **kwargs):
        is_owner = kwargs.pop('is_owner', True)
        is_maintainer = kwargs.pop('is_maintainer', True)
        super().__init__(*args, **kwargs)
        self.fields['maintainers'].queryset = self.instance.maintainers.all()
        self.fields['public'].label = "Visibility"

        # this block below is not necessarily true but it eases making restrictions for default collection 'bookmarks'
        if self.instance.is_default_collection:
            self.fields['name'].widget.attrs.update({'disabled': 'disabled'})
            self.fields['name'].help_text = "Your personal bookmarks collection's name can't be edited."
            self.fields['public'].widget.attrs.update({'disabled':'disabled'})
            self.fields['public'].help_text = "Your personal bookmarks collection is private."

        if not self.fields['maintainers'].queryset:
            self.fields['maintainers'].help_text = "This collection doesn't have any maintainers"
        
        owner_fields = ['name', 'description', 'public', 'maintainers', 'collection_maintainers']
        if not is_owner:
            for field in owner_fields:
                self.fields[field].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        clean_data = super().clean()

        if clean_data['name'] != self.instance.name:
            if Collection.objects.filter(user=self.instance.user, name=clean_data['name']).exists():
                self.add_error('name', forms.ValidationError("You already have a collection with this name"))
        
        return super().clean()
    
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
        current_sounds = list(Sound.objects.filter(collectionsound__collection=collection).values_list('id', flat=True))
        for snd in new_sounds:
            if snd not in current_sounds:
                sound = Sound.objects.get(id=snd)
                cs = CollectionSound(user=user_adding_sound, sound=sound, collection=collection)
                if user_adding_sound == collection.user:
                    cs.status = 'OK'
                cs.save()                
                collection.num_sounds += 1
            else:
                current_sounds.remove(snd)
        for snd in current_sounds:
            sound = Sound.objects.get(id=snd)
            cs = CollectionSound.objects.get(collection=collection, sound=sound)
            cs.delete()
            collection.num_sounds -= 1
            
        new_maintainers = self.clean_ids_field('collection_maintainers')
        current_maintainers = list(User.objects.filter(collection_maintainer=collection).values_list('id', flat=True))
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
        fields = ('name', 'description', 'public', 'maintainers')
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols': 50}),
            'maintainers': forms.CheckboxSelectMultiple(attrs={'class': 'bw-checkbox'}),
            'public': forms.RadioSelect(choices=[(True, 'Public'), (False, 'Private')], attrs={'class': 'bw-radio'})
        }

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
    maintainer = forms.CharField(
        widget=TextInput(attrs={'placeholder': "Fill in the username of the maintainer"}),
        label=False, 
        help_text=None, 
        max_length=128, 
        required=False)
    
    collection = None
    
    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection', False)
        super().__init__(*args, **kwargs)
    # with the new behaviour of the addMaintainersModal, we don't validate the form anymore
    # TODO: look for a way so that these validation errors can be displayed in the modal when performing queries
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
    
# NOTE: adding maintainers will be done frome edit collection page using a modal to introduce
# username
class CollectionMaintainerForm(forms.Form):
    collection = forms.ChoiceField(
        label=False,
        choices=[], 
        required=True)
    
    use_last_collection = forms.BooleanField(widget=forms.HiddenInput(), required=False, initial=False)
    user_collections = None
    user_available_collections = None

    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop('user_collections', False)
        self.user_adding_maintainer = kwargs.pop('user_adding_maintainer', False)
        self.maintainer_id = kwargs.pop('maintainer_id', False)
        
        if self.user_collections:
            # the available collections are: from the user's collections, the ones in which the maintainer is not a maintaner still
            self.user_available_collections = Collection.objects.filter(id__in=self.user_collections).exclude(maintainers__id=self.maintainer_id)

        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = ([(collection.id, collection.name) for collection in self.user_available_collections]
                                              if self.user_available_collections else [])
        
    
    def save(self, *args, **kwargs):
        # this function returns de selected collection
        collection_to_use = Collection.objects.get(id=self.cleaned_data['collection'])
        return collection_to_use
