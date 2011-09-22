from django import forms
from django.contrib.auth.models import User
from utils.forms import RecaptchaForm, HtmlCleaningCharField

class ManualUserField(forms.CharField):
    def clean(self, value):
        if not value:
            raise forms.ValidationError('Please enter a username.')
        try:
            return User.objects.get(username__iexact=value)
        except User.DoesNotExist: #@UndefinedVariable
            raise forms.ValidationError("We are sorry, but this username does not exist...")

class MessageReplyForm(RecaptchaForm):
    to = ManualUserField()
    subject = forms.CharField(min_length=3, max_length=128)
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))