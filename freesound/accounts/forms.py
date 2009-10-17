from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from models import Profile
from utils.forms import RecaptchaForm

class UploadFileForm(forms.Form):
    file = forms.FileField()

class FileChoiceForm(forms.Form):
    files = forms.MultipleChoiceField()
    
    def __init__(self, choices, *args, **kwargs):
        super(FileChoiceForm, self).__init__(*args, **kwargs)
        self.fields['files'].choices = choices


class RegistrationForm(RecaptchaForm):
    username = forms.RegexField(label=_("Username"), min_length=3, max_length=30, regex=r'^\w+$',
        help_text = _("Required. 30 characters or fewer. Alphanumeric characters only (letters, digits and underscores)."),
        error_message = _("This value must contain only letters, numbers and underscores."))
    first_name = forms.CharField(help_text = _("Optional."), required=False)
    last_name = forms.CharField(help_text=_("Optional."), required=False)
    email1 = forms.EmailField(label=_("Email"), help_text = _("We will send you a confirmation/activation email, so make sure this is correct!."))
    email2 = forms.EmailField(label=_("Email confirmation"))
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput)
    newsletter = forms.BooleanField(label=_("Sign up for the newsletter (only once every 4 months or so)?"), required=False, initial=True)

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username__iexact=username)
        except User.DoesNotExist: #@UndefinedVariable
            return username
        raise forms.ValidationError(_("A user with that username already exists."))

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def clean_email2(self):
        email1 = self.cleaned_data.get("email1", "")
        email2 = self.cleaned_data["email2"]
        if email1 != email2:
            raise forms.ValidationError(_("The two email fields didn't match."))
        try:
            User.objects.get(email__iexact=email2)
            raise forms.ValidationError(_("A user using that email address already exists."))
        except User.DoesNotExist:
            pass
        return email2

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email2"]
        password = self.cleaned_data["password2"]
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("flast_name", "")
        newsletter = self.cleaned_data.get("newsletter", False)

        user = User(username=username, first_name=first_name, last_name=last_name, email=email, password=password,is_staff=False, is_active=False, is_superuser=False)
        user.set_password(password)
        user.save()
        
        profile = Profile(user=user, wants_newsletter=newsletter)
        profile.save()

        return user