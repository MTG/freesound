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

def MessageReplyClassCreator(baseclass):
    class MessageReplyForm(baseclass):
        to = ManualUserField(widget=forms.TextInput(attrs={'size':'40'}))
        subject = forms.CharField(min_length=3, max_length=128, widget=forms.TextInput(attrs={'size':'80'}))
        body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))
    return MessageReplyForm

MessageReplyForm = MessageReplyClassCreator(RecaptchaForm)
MessageReplyFormNoCaptcha = MessageReplyClassCreator(forms.Form)