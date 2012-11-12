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
#from django.forms import ModelForm, TextInput, Select
from bookmarks.models import BookmarkCategory, Bookmark

class BookmarkCategoryForm(forms.ModelForm):
    
    class Meta:
        model = BookmarkCategory
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'class':'category_name_widget'}),
        }

class BookmarkForm(forms.ModelForm):
    new_category_name = forms.CharField(max_length=128, help_text="<br>If you want a new category, don't select one above, set its new name here.", required=False)

    class Meta:
        model = Bookmark
        fields = ('name','category')
        widgets = {
            'name': forms.TextInput(attrs={'class':'name_widget'}),
        }
    
    def save(self):
        
        try:
            bookmark = Bookmark(user=self.instance.user,sound=self.instance.sound)
            
            if not self.cleaned_data['category']:
                if self.cleaned_data['new_category_name'] != "":
                    category = BookmarkCategory(user=self.instance.user, name=self.cleaned_data['new_category_name'])
                    category.save()
                    bookmark.category = category
                    self.cleaned_data['category'] = category
            else:
                bookmark.category = self.cleaned_data['category']
            
            if self.cleaned_data['name'] != "":
                bookmark.name = self.cleaned_data['name']
            
            bookmark.save()
            return True
        
        except:
            return False