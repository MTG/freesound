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
from fscollections.models import Collection

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

    NO_COLLECTION_CHOICE_VALUE = '-1'
    NEW_COLLECTION_CHOICE_VALUE = '0'

    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop('user_collections', False)
        self.user_saving_sound = kwargs.pop('user_saving_sound', False)
        self.sound_id = kwargs.pop('sound_id', False)
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = [(self.NO_COLLECTION_CHOICE_VALUE, '--- No collection ---'),#in this case this goes to bookmarks collection (might have to be created)
                                           (self.NEW_COLLECTION_CHOICE_VALUE, 'Create a new collection...')] + \
                                           ([(collection.id, collection.name) for collection in self.user_collections]
                                            if self.user_collections else[])
        
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
                        Collection(user=self.user_saving_bookmark, name=self.cleaned_data['new_collection_name'])
                    collection.save()
                    collection_to_use = collection
            else:
                collection_to_use = Collection.objects.get(id=self.cleaned_data['collection'])
        else: #en aquest cas - SÍ estem fent servir l'última coleccio, NO estem creant una nova coleccio, NO estem agafant una coleccio existent i 
            # per tant ens trobem en un cas de NO COLLECTION CHOICE VALUE (no s'ha triat cap coleccio)
            # si no es tria cap coleccio: l'usuari té alguna colecció? NO -> creem BookmarksCollection pels seus sons privats
            # SI -> per defecte es posa a BookmarksCollection
            try:
                last_user_collection = \
                    Collection.objects.filter(user=self.user_saving_bookmark).order_by('-created')[0]
                # If user has a previous bookmark, use the same category (or use none if no category used in last
                # bookmark)
                collection_to_use = last_user_collection
            except IndexError:
                # This is first bookmark of the user
                pass

        # If collection already exists, don't save it and return the existing one
        collection, _ = Collection.objects.get_or_create(
            name = collection_to_use.name, user=self.user_saving_bookmark)
        return collection