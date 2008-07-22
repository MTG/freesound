from django import newforms as forms

class UploadFileForm(forms.Form):
    file = forms.FileField()

class FileChoiceForm(forms.Form):
    files = forms.MultipleChoiceField()
    
    def __init__(self, choices, *args, **kwargs):
        super(FileChoiceForm, self).__init__(*args, **kwargs)
        self.fields['files'].choices = choices
