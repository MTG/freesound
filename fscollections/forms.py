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
from django.forms import ModelForm, Textarea, TextInput, SelectMultiple
from django.contrib.auth.models import User
from fscollections.models import Collection, CollectionSound
from utils.forms import HtmlCleaningCharField

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

    NO_COLLECTION_CHOICE_VALUE = '-1'
    NEW_COLLECTION_CHOICE_VALUE = '0'

    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop('user_collections', False)
        self.user_saving_sound = kwargs.pop('user_saving_sound', False)
        self.sound_id = kwargs.pop('sound_id', False)

        if self.user_collections:
            self.user_available_collections = Collection.objects.filter(id__in=self.user_collections).exclude(collectionsound__sound__id=self.sound_id)
        
        # NOTE: as a provisional solution to avoid duplicate sounds in a collection, Collections already containing the sound are not selectable
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = [(self.NO_COLLECTION_CHOICE_VALUE, '--- No collection ---'),#in this case this goes to bookmarks collection (might have to be created)
                                           (self.NEW_COLLECTION_CHOICE_VALUE, 'Create a new collection...')] + \
                                           ([(collection.id, collection.name) for collection in self.user_available_collections ]
                                            if self.user_available_collections else[])
        
        self.fields['new_collection_name'].widget.attrs['placeholder'] = "Fill in the name for the new collection"
        self.fields['collection'].widget.attrs = {
            'data-grey-items': f'{self.NO_COLLECTION_CHOICE_VALUE},{self.NEW_COLLECTION_CHOICE_VALUE}'}
    
    def save(self, *args, **kwargs):
        collection_to_use = None

        if not self.cleaned_data['use_last_collection']:
            if self.cleaned_data['collection'] == self.NO_COLLECTION_CHOICE_VALUE:
                pass
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
        sound = self.sound_id
        if CollectionSound.objects.filter(collection=collection,sound=sound).exists():
            raise forms.ValidationError("This sound already exists in the collection")
        
        return super().clean()
    
class CollectionEditForm(forms.ModelForm):

    class Meta():
        model = Collection
        fields = ('name', 'description','maintainers')
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols': 50}),
            'maintainers': forms.CheckboxSelectMultiple(attrs={'class': 'bw-checkbox'})
        }

    def __init__(self, *args, **kwargs):
        is_owner = kwargs.pop('is_owner', True)
        super().__init__(*args, **kwargs)
        self.fields['maintainers'].queryset = self.instance.maintainers.all()
        
        if not is_owner:
            for field in self.fields:
                self.fields[field].widget.attrs['readonly'] = 'readonly'

class MaintainerForm(forms.Form):
    maintainer = forms.CharField(
        label=False, 
        help_text=None, 
        max_length=128, 
        required=True)
    
    collection = None
    
    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection', False)
        super().__init__(*args, **kwargs)
        self.fields['maintainer'].widget.attrs['placeholder'] = "Fill in the username of the maintainer"

    def clean(self):
        try:
            new_maintainer = User.objects.get(username=self.cleaned_data['maintainer'])
            if new_maintainer in self.collection.maintainers.all():
                raise forms.ValidationError("The user is already a maintainer")
            return super().clean()
        except User.DoesNotExist:
            raise forms.ValidationError("The user does not exist")

        return super().clean()
    
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
