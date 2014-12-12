#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from accounts.models import Profile
from utils.forms import RecaptchaForm, HtmlCleaningCharField
from utils.spam import is_spam

class UploadFileForm(forms.Form):
    file = forms.FileField()

class  TermsOfServiceForm(forms.Form):
    accepted_tos  = forms.BooleanField(label='',
                                       help_text='Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> of the Freesound website',
                                       required=True,
                                       error_messages={'required': 'You must accept the terms of use in order to continue using Freesound.'})

class AvatarForm(forms.Form):
    file = forms.FileField(required=False)
    remove = forms.BooleanField(label="Remove avatar", required=False)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        file_cleaned = cleaned_data.get("file", None)
        remove_cleaned = cleaned_data.get("remove", False)

        if remove_cleaned and file_cleaned:
            raise forms.ValidationError("Either remove or select a new avatar, you can't do both at the same time.")
        elif not remove_cleaned and not file_cleaned:
            raise forms.ValidationError("You forgot to select a file.")

        # Always return the full collection of cleaned data.
        return cleaned_data
    

class FileChoiceForm(forms.Form):
    files = forms.MultipleChoiceField()
    
    def __init__(self, files, *args, **kwargs):
        super(FileChoiceForm, self).__init__(*args, **kwargs)
        choices = files.items()
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
    newsletter = forms.BooleanField(label=_(""),
                                    required=False,
                                    initial=True,
                                    help_text=_("Sign up for the newsletter (only once every 4 months or so)?"))
    accepted_tos = forms.BooleanField(label='',
                                       help_text=_('Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> of the Freesound website'),
                                       required=True,
                                       error_messages={'required': _('You must accept the terms of use in order to register to Freesound.')})


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
        except User.DoesNotExist: #@UndefinedVariable
            pass
        
        if email2.lower().endswith("@aol.com"):
            raise forms.ValidationError(_("We are sorry, but aol.com deletes all our emails before they reach you, please use a different provider."))
        
        return email2

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email2"]
        password = self.cleaned_data["password2"]
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")
        newsletter = self.cleaned_data.get("newsletter", False)
        accepted_tos = self.cleaned_data.get("accepted_tos", False)

        user = User(username=username, first_name=first_name, last_name=last_name, email=email, password=password,is_staff=False, is_active=False, is_superuser=False)
        user.set_password(password)
        user.save()
        
        profile = Profile(user=user, wants_newsletter=newsletter, accepted_tos=accepted_tos)
        profile.save()

        return user


class ReactivationForm(forms.Form):
    user = forms.CharField(label="The username or email you signed up with")
    
    def clean_user(self):
        username_or_email = self.cleaned_data["user"]
        
        try:
            return User.objects.get(email__iexact=username_or_email, is_active=False)
        except User.DoesNotExist: #@UndefinedVariable
            pass
        
        try:
            return User.objects.get(username__iexact=username_or_email, is_active=False)
        except User.DoesNotExist: #@UndefinedVariable
            pass
        
        raise forms.ValidationError(_("No non-active user with such email or username exists."))


class UsernameReminderForm(forms.Form):
    user = forms.EmailField(label="The email address you signed up with")
    
    def clean_user(self):
        email = self.cleaned_data["user"]
        
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist: #@UndefinedVariable
            raise forms.ValidationError(_("No user with such an email exists."))

class ProfileForm(forms.ModelForm):
    about = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(rows=20, cols=70)), required=False)
    signature = HtmlCleaningCharField(label="Forum signature", widget=forms.Textarea(attrs=dict(rows=20, cols=70)), required=False)
    wants_newsletter = forms.BooleanField(label="Subscribed to newsletter", required=False)
    enabled_stream_emails = forms.BooleanField(label="Receive weekly email notifications with new uploaded sounds by users and tags you follow", required=False)
    not_shown_in_online_users_list = forms.BooleanField(label="Hide from \"users currently online\" list in the People page", required=False)
    
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_about(self):
        about = self.cleaned_data['about']
        if is_spam(self.request, about):
            raise forms.ValidationError("Your 'about' text was considered spam, please edit and resubmit. If it keeps failing please contact the admins.")
        return about

    def clean_signature(self):
        signature = self.cleaned_data['signature']
        if is_spam(self.request, signature):
            raise forms.ValidationError("Your signature was considered spam, please edit and resubmit. If it keeps failing please contact the admins.")
        return signature

    class Meta:
        model = Profile
        fields = ('home_page', 'wants_newsletter', 'enabled_stream_emails', 'about', 'signature', 'not_shown_in_online_users_list')
        

class EmailResetForm(forms.Form):   
    email = forms.EmailField(label=_("New e-mail address"), max_length=75)
    password = forms.CharField(label=_("Your password"), widget=forms.PasswordInput)
    
    # Using init function to pass user variable so later we can perform check_password in clean_password function
    def __init__(self, *args, **kwargs):    
        self.user = kwargs.pop('user', None)
        super(EmailResetForm, self).__init__(*args, **kwargs)
 
    def clean_password(self):
        if not self.user.check_password(self.cleaned_data["password"]) :
            raise forms.ValidationError(_("Incorrect password."))    
        
    