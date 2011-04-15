from django import forms
from models import Ticket
from utils.forms import RecaptchaForm

class UserMessageForm(forms.Form):
    message     = forms.CharField(widget=forms.Textarea)

class UserContactForm(UserMessageForm):
    title       = forms.CharField() 
    
class AnonymousMessageForm(RecaptchaForm):
    message     = forms.CharField(widget=forms.Textarea)

class AnonymousContactForm(AnonymousMessageForm):
    title       = forms.CharField()
    email       = forms.EmailField()
