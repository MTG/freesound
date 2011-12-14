from django.forms import ModelForm, TextInput, Textarea
from bookmarks.models import BookmarkCategory, Bookmark

class BookmarkCategoryForm(ModelForm):
    
    class Meta:
        model = BookmarkCategory
        fields = ('name',)
        widgets = {
            'name': TextInput(attrs={'style':'width:230px;height:10px;font-size:10px;'}),
        }
        
class BookmarkForm(ModelForm):
    
    class Meta:
        model = Bookmark
        fields = ('name','category')