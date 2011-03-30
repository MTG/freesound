from django import forms
from models import Ticket

        
class UserContactForm(forms.Form):
    message     = forms.CharField(widget=forms.Textarea) 
    
class AnonymousContactForm(forms.Form):
    message     = forms.CharField(widget=forms.Textarea)
    email        = forms.EmailField()
    
