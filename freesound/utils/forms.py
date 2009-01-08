from django import forms
from utils.text_utils import clean_html, is_shouting

class HtmlCleaningCharField(forms.CharField):
    def clean(self, value):
        value = super(HtmlCleaningCharField, self).clean(value)
        
        if is_shouting(value):
            raise forms.ValidationError('Please moderate the amount of upper case characters in your post...')
        
        return clean_html(value)