from django.forms import ModelForm, TextInput, Textarea
from bookmarks.models import BookmarkCategory

class BookmarkCategoryForm(ModelForm):
    
    class Meta:
        model = BookmarkCategory
        fields = ('name',)#'description',)
        widgets = {
            'name': TextInput(attrs={'style':'width:230px;height:10px;font-size:10px;'}),
            #'description': Textarea(attrs={'style':'width:252px;height:40px'}),
        }
        