from django import forms
from utils.forms import HtmlCleaningCharField
from utils.spam import is_spam

class CommentForm(forms.Form):
    comment = HtmlCleaningCharField(widget=forms.Textarea)
    
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(CommentForm, self).__init__(*args, **kwargs)
    
    def clean_comment(self):
        comment = self.cleaned_data['comment']

        if is_spam(self.request, comment):
            raise forms.ValidationError("Your comment was considered spam, please edit and repost. If it keeps failing please contact the admins.")
        
        return comment
