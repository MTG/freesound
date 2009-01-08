from django import forms
from utils.forms import HtmlCleaningCharField

class PostReplyForm(forms.Form):
    body = HtmlCleaningCharField(widget=forms.Textarea)

    def __init__(self, quote, *args, **kwargs):
        self.quote = quote
        super(PostReplyForm, self).__init__(*args, **kwargs)
    
    def clean_body(self):
        body = self.cleaned_data['body']
        if self.quote and body.strip() == self.quote:
            raise forms.ValidationError("You should type something...")
        return body