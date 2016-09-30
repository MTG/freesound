# -*- coding: utf-8 -*-
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

import time
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from multiupload.fields import MultiFileField
from django.conf import settings
from accounts.models import Profile
from utils.forms import HtmlCleaningCharField, filename_has_valid_extension, CaptchaWidget
from utils.spam import is_spam
from utils.encryption import decrypt, encrypt

def validate_file_extension(audiofiles):
    try:
        for file_ in audiofiles:
            content_type = file_.content_type
            if filename_has_valid_extension(str(file_)):
                ext = str(file_).rsplit('.', 1)[-1].lower()
                if ext == 'flac':
                    # At least Safari and Firefox do not set the proper mime type for .flac files
                    # (use 'application/octet-stream' instead of 'audio/flac'). For this reason we also allow
                    # this mime type for flac files.
                    if not content_type.startswith("audio") and not content_type == 'application/octet-stream':
                        raise forms.ValidationError('Uploaded file format not supported or not an audio file.')
                else:
                    if not content_type.startswith("audio"):
                        raise forms.ValidationError('Uploaded file format not supported or not an audio file.')
            else:
                raise forms.ValidationError('Uploaded file format not supported or not an audio file.')

    except AttributeError:
        # Will happen when uploading with the flash uploader
        if not filename_has_valid_extension(str(audiofiles)):
            raise forms.ValidationError('Uploaded file format not supported or not an audio file.')


class UploadFileForm(forms.Form):
    files = MultiFileField(min_num=1, validators=[validate_file_extension], label="")


class FlashUploadFileForm(forms.Form):
    file = forms.FileField(validators=[validate_file_extension])


class TermsOfServiceForm(forms.Form):
    accepted_tos = forms.BooleanField(
        label='',
        help_text='Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> of the '
                  'Freesound website',
        required=True,
        error_messages={'required': 'You must accept the terms of use in order to continue using Freesound.'}
    )


class AvatarForm(forms.Form):
    file = forms.FileField(required=False, label="")
    remove = forms.BooleanField(help_text="Remove avatar", label="", required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        file_cleaned = cleaned_data.get("file", None)
        remove_cleaned = cleaned_data.get("remove", False)

        if remove_cleaned and file_cleaned:
            raise forms.ValidationError("Either remove or select a new avatar, you can't do both at the same time.")
        elif not remove_cleaned and not file_cleaned:
            raise forms.ValidationError("You forgot to select a file.")

        return cleaned_data


class FileChoiceForm(forms.Form):
    files = forms.MultipleChoiceField()

    def __init__(self, files, *args, **kwargs):
        super(FileChoiceForm, self).__init__(*args, **kwargs)
        choices = files.items()
        self.fields['files'].choices = choices


class RegistrationForm(forms.Form):
    captcha_key = settings.RECAPTCHA_PUBLIC_KEY
    recaptcha_response = forms.CharField(widget=CaptchaWidget)
    username = forms.RegexField(
        label=_("Username"),
        min_length=3,
        max_length=30,
        regex=r'^\w+$',
        help_text=_("Required. 30 characters or fewer. Alphanumeric characters only (letters, digits and underscores)."),
        error_messages={'only_letters': _("This value must contain only letters, numbers and underscores.")}
    )
    first_name = forms.CharField(help_text=_("Optional."), max_length=30, required=False)
    last_name = forms.CharField(help_text=_("Optional."), max_length=30, required=False)
    email1 = forms.EmailField(label=_("Email"), help_text=_("We will send you a confirmation/activation email, so make "
                                                            "sure this is correct!."))
    email2 = forms.EmailField(label=_("Email confirmation"))
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput)
    newsletter = forms.BooleanField(
        label=_(""),
        required=False,
        initial=True,
        help_text=_("Sign up for the newsletter (only once every 4 months or so)?")
    )
    accepted_tos = forms.BooleanField(
        label='',
        help_text=_('Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> of the '
                    'Freesound website'),
        required=True,
        error_messages={'required': _('You must accept the terms of use in order to register to Freesound.')}
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username__iexact=username)
        except User.DoesNotExist:
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

    def clean_recaptcha_response(self):
        captcha_response = self.cleaned_data.get("recaptcha_response")
        if not captcha_response:
            raise forms.ValidationError(_("Captcha is not correct"))
        return captcha_response

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email2"]
        password = self.cleaned_data["password2"]
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")
        newsletter = self.cleaned_data.get("newsletter", False)
        accepted_tos = self.cleaned_data.get("accepted_tos", False)

        user = User(username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    is_staff=False,
                    is_active=False,
                    is_superuser=False)
        user.set_password(password)
        user.save()

        profile = user.profile  # .profile created on User.save()
        profile.wants_newsletter = newsletter
        profile.accepted_tos = accepted_tos
        profile.save()

        return user


class ReactivationForm(forms.Form):
    user = forms.CharField(label="The username or email you signed up with")

    def clean_user(self):
        username_or_email = self.cleaned_data["user"]
        try:
            return User.objects.get(email__iexact=username_or_email, is_active=False)
        except User.DoesNotExist:
            pass
        try:
            return User.objects.get(username__iexact=username_or_email, is_active=False)
        except User.DoesNotExist:
            pass
        raise forms.ValidationError(_("No non-active user with such email or username exists."))


class FsAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super(FsAuthenticationForm, self).__init__(*args, **kwargs)
        self.error_messages.update({
            'inactive': mark_safe(_("You are trying to log in with an inactive account, please <a href=\"%s\">activate "
                                    "your account</a> first." % reverse("accounts-resend-activation")))
        })


class UsernameReminderForm(forms.Form):
    user = forms.EmailField(label="The email address you signed up with")

    def clean_user(self):
        email = self.cleaned_data["user"]
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError(_("No user with such an email exists."))


class ProfileForm(forms.ModelForm):
    about = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(rows=20, cols=70)), required=False)
    signature = HtmlCleaningCharField(
        label="Forum signature",
        widget=forms.Textarea(attrs=dict(rows=20, cols=70)),
        required=False
    )
    wants_newsletter = forms.BooleanField(help_text="Subscribed to newsletter", label="", required=False)
    is_adult = forms.BooleanField(help_text="I'm an adult, I can deal with explicit content",
        label="", required=False)
    enabled_stream_emails = forms.BooleanField(
        help_text="Receive weekly stream update email notifications (only when new sounds are uploaded by "
                  "users you follow or that have tags you follow)",
        label = "",
        required=False
    )
    not_shown_in_online_users_list = forms.BooleanField(
        help_text="Hide from \"users currently online\" list in the People page",
        label = "",
        required=False
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_about(self):
        about = self.cleaned_data['about']
        if is_spam(self.request, about):
            raise forms.ValidationError("Your 'about' text was considered spam, please edit and resubmit. If it keeps "
                                        "failing please contact the admins.")
        return about

    def clean_signature(self):
        signature = self.cleaned_data['signature']
        if is_spam(self.request, signature):
            raise forms.ValidationError("Your signature was considered spam, please edit and resubmit. If it keeps "
                                        "failing please contact the admins.")
        return signature

    class Meta:
        model = Profile
        fields = ('home_page', 'is_adult', 'wants_newsletter',
                  'enabled_stream_emails', 'about', 'signature',
                  'not_shown_in_online_users_list')


class EmailResetForm(forms.Form):
    email = forms.EmailField(label=_("New e-mail address"), max_length=75)
    password = forms.CharField(label=_("Your password"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # Using init function to pass user variable so later we can perform check_password in clean_password function
        self.user = kwargs.pop('user', None)
        super(EmailResetForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        if not self.user.check_password(self.cleaned_data["password"]):
            raise forms.ValidationError(_("Incorrect password."))

DELETE_CHOICES = [('only_user', mark_safe(u'Delete only my user account information :)  (see <a href="/help/faq/#how-do-i-delete-myself-from-your-site" target="_blank">here</a> for more information)')),
                  ('delete_sounds', u'Delete also my sounds and packs :(')]

class DeleteUserForm(forms.Form):
    encrypted_link = forms.CharField(widget=forms.HiddenInput())
    delete_sounds = forms.ChoiceField(choices = DELETE_CHOICES,
            widget=forms.RadioSelect())

    def clean_encrypted_link(self):
        data = self.cleaned_data['encrypted_link']
        if not data:
            raise PermissionDenied
        user_id, now = decrypt(data).split("\t")
        user_id = int(user_id)
        if user_id != self.user_id:
            raise PermissionDenied
        link_generated_time = float(now)
        if abs(time.time() - link_generated_time) > 10:
            raise forms.ValidationError("Time expired")
        return data

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id')
        encrypted_link = encrypt(u"%d\t%f" % (self.user_id, time.time()))
        kwargs['initial'] = {
                'delete_sounds': 'only_user',
                'encrypted_link': encrypted_link
                }
        super(DeleteUserForm, self).__init__(*args, **kwargs)

