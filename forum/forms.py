from django import forms
from utils.forms import HtmlCleaningCharField
from utils.spam import is_spam

class PostReplyForm(forms.Form):
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))
    subscribe = forms.BooleanField(help_text="Send me an email notification when new posts are added in this thread.", required=False, initial=True)
    def __init__(self, request, quote, *args, **kwargs):
        self.request = request
        self.quote = quote
        super(PostReplyForm, self).__init__(*args, **kwargs)

    def clean_body(self):
        body = self.cleaned_data['body']

        if self.quote and body.strip() == self.quote:
            raise forms.ValidationError("You should type something...")

        if is_spam(self.request, body):
            raise forms.ValidationError("Your post was considered spam, please edit and repost. If it keeps failing please contact the admins.")

        return body

class NewThreadForm(forms.Form):
    title = forms.CharField()
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))
    subscribe = forms.BooleanField(help_text="Send me an email notification when new posts are added in this thread.", required=False, initial=True)
