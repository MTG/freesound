from django import forms
from utils.forms import HtmlCleaningCharField

class CommentForm(forms.Form):
    comment = HtmlCleaningCharField(widget=forms.Textarea)
