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




# Sound moderation forms
MODERATION_CHOICES = [('Approve', 'Approve'),
                      ('Delete', 'Delete'),
                      ('Defer', 'Defer'),
                      ('Return', 'Return')]

class SoundModerationForm(forms.Form):
    action      = forms.ChoiceField(choices=MODERATION_CHOICES,
                                    required=True, 
                                    widget=forms.RadioSelect(),
                                    label='')
    ticket      = forms.IntegerField(widget=forms.widgets.HiddenInput)


class ModerationReturnMessageForm(forms.Form):
    custom      = forms.CharField(widget=forms.Textarea,
                                  required=False,
                                  label='Custom message')
    
    
def __define_moderation_message_class(name, choices):
    return type(name,
                (forms.Form,),
                dict(predefined = forms.ChoiceField(choices=choices+[('', '------')],
                                                    required=False, 
                                                    label='Predefined message'),
                     custom     = forms.CharField(widget=forms.Textarea,
                                                  required=False,
                                                  label='Custom message')))
        
ModerationDeleteMessageForm = \
    __define_moderation_message_class('ModerationDeleteMessageForm',
[("""The sound has an incompatible format and can't be processed by
Freesound. Please convert your file to a different format, such as
mp3, wav, or ogg, and upload it again.""",
'Incompatible'),
("""The sound you have uploaded is illegal or we suspect you do not 
own the copyright. Please do not upload it again.""",
'Illegal'),
("""You've uploaded a file that doesn't fit with the type of content 
Freesound is looking for. Songs, for example, shouldn't be on Freesound""",
'Not a sound')]) 
    
ModerationDeferMessageForm = \
    __define_moderation_message_class('ModerationDeferMessageForm',
[("""The tags you've chosen are not enough. Please add descriptive tags
and as many as you can.""",
'Insufficient tags'),
("""The description is not good enough. Please be as descriptive as you
can and add as many details as you can think of.""",
'Insufficient description'),
("""The tags and description are not good enough. Please be as 
descriptive as you can and add as many details as you can think of.""",
'Insufficient tags and description')])

