from django import forms
from utils.forms import RecaptchaForm

class ContactForm(RecaptchaForm):
    your_email = forms.EmailField()
    subject = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 10, 'cols': 50}))