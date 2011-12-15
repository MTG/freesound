from django.forms import ModelForm, TextInput, Textarea
from bookmarks.models import BookmarkCategory, Bookmark

class BookmarkCategoryForm(ModelForm):
    
    class Meta:
        model = BookmarkCategory
        fields = ('name',)
        widgets = {
            'name': TextInput(attrs={'class':'category_name_widget'}),
        }
'''        
class BookmarkForm(ModelForm):
    
    class Meta:
        model = Bookmark
        fields = ('name','category')
'''