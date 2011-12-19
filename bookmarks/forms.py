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
    new_category_name = forms.CharField(max_length=128, help_text="If you want a new category, don't select one above, set its new name here.", required=False)

    class Meta:
        model = Bookmark
        fields = ('name','category')
        widgets = {
            'name': forms.TextInput(attrs={'class':'name_widget'}),
        }
    
    def save(self):
        
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