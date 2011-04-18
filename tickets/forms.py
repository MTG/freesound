from django import forms
from models import UserAnnotation
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

# Sound moderation forms
MODERATION_CHOICES = [(x,x) for x in \
                      ['Approve', 
                       'Delete', 
                       'Defer', 
                       'Return']]

class SoundModerationForm(forms.Form):
    action      = forms.ChoiceField(choices=MODERATION_CHOICES,
                                    required=True, 
                                    widget=forms.RadioSelect(),
                                    label='')
    ticket      = forms.IntegerField(widget=forms.widgets.HiddenInput)

class ModerationMessageForm(forms.Form):
    message      = forms.CharField(widget=forms.Textarea,
                                   required=False,
                                   label='')

class UserAnnotationForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea,
                           required=True,
                           label='')
    
        
