from django import newforms as forms

class UploadFileForm(forms.Form):
    file = forms.FileField()
    unique_id = forms.HiddenInput()
