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

import logging

from captcha.fields import ReCaptchaField
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.safestring import mark_safe
from multiupload.fields import MultiFileField
from django.core.signing import BadSignature, SignatureExpired

from accounts.models import Profile, EmailPreferenceType, OldUsername, DeletedUser
from utils.encryption import sign_with_timestamp, unsign_with_timestamp
from utils.forms import HtmlCleaningCharField, HtmlCleaningCharFieldWithCenterTag, filename_has_valid_extension
from utils.spam import is_spam

web_logger = logging.getLogger('web')


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
                elif ext == 'ogg':
                    # Firefox seems to set wrong mime type for ogg files to video/ogg instead of audio/ogg.
                    # Also safari seems to use 'application/octet-stream'.
                    # For these reasons we also allow extra mime types for ogg files.
                    print(content_type)
                    if not content_type.startswith("audio") and not content_type == 'video/ogg' and not content_type == 'application/octet-stream':
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


def validate_csvfile_extension(csv_file):
    csv_filename = str(csv_file)
    if not ('.' in csv_filename and csv_filename.rsplit('.', 1)[-1].lower() in settings.ALLOWED_CSVFILE_EXTENSIONS):
        raise forms.ValidationError('Invalid file extension.')


class BulkDescribeForm(forms.Form):
    csv_file = forms.FileField(label='', validators=[validate_csvfile_extension])

class UploadFileForm(forms.Form):
    files = MultiFileField(min_num=1, validators=[validate_file_extension], label="", required=False)


class FlashUploadFileForm(forms.Form):
    file = forms.FileField(validators=[validate_file_extension])


class TermsOfServiceForm(forms.Form):
    accepted_tos = forms.BooleanField(
        label='',
        help_text='Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> '
                  'and the <a href="/help/privacy/" target="_blank">privacy policy</a> of Freesound (required)',
        required=True,
        error_messages={'required': 'You must accept the terms of use and the privacy poclicy in order to continue '
                                    'using Freesound.'}
    )
    accepted_license_change = forms.BooleanField(
        label='',
        help_text='Check this box to upgrade your Creative Commons 3.0 licenses to 4.0',
        required=False
    )
    next = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['accepted_tos'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['accepted_license_change'].widget.attrs['class'] = 'bw-checkbox'


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
        super().__init__(*args, **kwargs)
        choices = list(files.items())
        self.fields['files'].choices = choices


def get_user_by_email(email):
    return User.objects.get(email__iexact=email)


class UsernameField(forms.CharField):
    """ Username field, 3~30 characters, allows only alphanumeric chars, required by default """
    def __init__(self, required=True):
        super().__init__(
            label="Username",
            min_length=3,
            max_length=30,
            validators=[RegexValidator(r'^[\w.+-]+$')],  # is the same as Django UsernameValidator except for '@' symbol
            help_text="30 characters or fewer. Can contain: letters, digits, underscores, dots, dashes and plus signs.",
            error_messages={'invalid': "This value must contain only letters, digits, underscores, dots, dashes and "
                                       "plus signs."},
            required=required)


def username_taken_by_other_user(username):
    """
    Check if a given username is already taken and can't be used for newly created users. Only usernames which
    are not being used by existing User objects, OldUsername objects and DeletedUser objects are considered to be
    available.

    Args:
        username (str): username to check

    Returns:
        bool: True if the username is already taken (not available), False otherwise

    """
    try:
        User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        try:
            OldUsername.objects.get(username__iexact=username)
        except OldUsername.DoesNotExist:
            try:
                DeletedUser.objects.get(username__iexact=username)
            except DeletedUser.DoesNotExist:
                # Only if no User, OldUsername or DeletedUser objects exist with that username, we consider it not
                # being taken
                return False
    return True


class RegistrationForm(forms.Form):
    username = UsernameField()
    email1 = forms.EmailField(label=False, help_text=False, max_length=254)
    email2 = forms.EmailField(label=False, help_text=False, max_length=254)
    password1 = forms.CharField(label=False, help_text=False, widget=forms.PasswordInput)
    accepted_tos = forms.BooleanField(
        label=mark_safe('Check this box to accept our <a href="/help/tos_web/" target="_blank">terms of '
                        'use</a> and the <a href="/help/privacy/" target="_blank">privacy policy</a>'),
        required=True,
        error_messages={'required': 'You must accept the terms of use in order to register to Freesound'}
    )
    recaptcha = ReCaptchaField(label="")  # Note that this field needs to be the last to appear last in the form

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(auto_id='id_%s_registration'))
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['username'].label = False
        self.fields['username'].help_text = False
        self.fields['username'].widget.attrs['placeholder'] = 'Username (30 characters maximum)'
        self.fields['email1'].widget.attrs['placeholder'] = 'Email'
        self.fields['email2'].widget.attrs['placeholder'] = 'Email confirmation'
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['accepted_tos'].widget.attrs['class'] = 'bw-checkbox'


    def clean_username(self):
        username = self.cleaned_data["username"]
        if not username_taken_by_other_user(username):
            return username
        raise forms.ValidationError("You cannot use this username to create an account")

    def clean_email2(self):
        email1 = self.cleaned_data.get("email1", "")
        email2 = self.cleaned_data["email2"]
        if email1 != email2:
            raise forms.ValidationError("Please confirm that your email address is the same in both fields")

    def clean_email1(self):
        email1 = self.cleaned_data["email1"]
        try:
            get_user_by_email(email1)
            web_logger.info('User trying to register with an already existing email (%s)', email1)
            raise forms.ValidationError("You cannot use this email address to create an account")
        except User.DoesNotExist:
            pass
        return email1

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email1"]
        password = self.cleaned_data["password1"]

        # NOTE: we create user "manually" instead of using "create_user" as we don't want 
        # is_active to be set to True automatically
        user = User(username=username,
                    email=email,
                    is_staff=False,
                    is_active=False,
                    is_superuser=False)
        user.set_password(password)
        user.save()
        return user


class ReactivationForm(forms.Form):
    user = forms.CharField(label="The username or email you signed up with", max_length=254)


class ProblemsLoggingInForm(forms.Form):
    username_or_email = forms.CharField(label="", help_text="", max_length=254)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username_or_email'].widget.attrs['placeholder'] = 'Your email or username'


class FsAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages.update({
            'inactive': mark_safe("You are trying to log in with an inactive account, please <a href=\"%s\">activate "
                                  "your account</a> first." % reverse("accounts-resend-activation")),
            'invalid_login': "Please enter a correct username/email and password. "
                             "Note that passwords are case-sensitive.",
        })
        self.fields['username'].label = False
        self.fields['username'].widget.attrs['placeholder'] = 'Enter your email or username'
        self.fields['password'].label = False
        self.fields['password'].widget.attrs['placeholder'] = 'Enter your password'


class UsernameReminderForm(forms.Form):
    user = forms.EmailField(label="The email address you signed up with", max_length=254)


class ProfileForm(forms.ModelForm):

    username = UsernameField(required=False)
    about = HtmlCleaningCharFieldWithCenterTag(
        widget=forms.Textarea(attrs=dict(rows=20, cols=70)), 
        required=False, 
        help_text=HtmlCleaningCharFieldWithCenterTag.make_help_text())
    signature = HtmlCleaningCharField(
        label="Forum signature",
        help_text=HtmlCleaningCharField.make_help_text(),
        widget=forms.Textarea(attrs=dict(rows=10, cols=70)),
        required=False,
        max_length=256,
    )
    sound_signature = HtmlCleaningCharField(
        label="Sound signature",
        widget=forms.Textarea(attrs=dict(rows=10, cols=70)),
        help_text="""Your sound signature is added to the end of each of your sound 
            descriptions. If you change the sound signature it will be automatically updated on all of your sounds. 
            Use the special text <code>${sound_url}</code> to refer to the URL of the current sound being displayed 
            and <code>${sound_id}</code> to refer to the id of the current sound. """ + HtmlCleaningCharField.make_help_text(),
        required=False,
        max_length=256,
    )
    is_adult = forms.BooleanField(label="I'm an adult, I don't want to see inappropriate content warnings",
                                  help_text=False, required=False)
    not_shown_in_online_users_list = forms.BooleanField(
        help_text="Hide from \"users currently online\" list in the People page",
        label="",
        required=False
    )

    allow_simultaneous_playback = forms.BooleanField(
        label="Allow simultaneous audio playback", required=False, widget=forms.CheckboxInput(attrs={'class': 'bw-checkbox'}))
    prefer_spectrograms = forms.BooleanField(
        label="Show spectrograms in sound players by default", required=False, widget=forms.CheckboxInput(attrs={'class': 'bw-checkbox'}))    

    def __init__(self, request, *args, **kwargs):
        self.request = request
        kwargs.update(initial={
            'username': request.user.username
        })
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        self.n_times_changed_username = OldUsername.objects.filter(user_id=self.request.user.id).count()
        if self.n_times_changed_username < 1:
            help_text = "You can only change your username %i times.<br><b>Warning</b>: once you " \
                        "change your username, you can't change it back to the previous username." \
                        % settings.USERNAME_CHANGE_MAX_TIMES
        elif 1 <= self.n_times_changed_username < settings.USERNAME_CHANGE_MAX_TIMES:
            help_text = "You can only change your username %i more time%s.<br><b>Warning</b>: once " \
                        "you change your username, you can't change it back to the previous username." \
                        % (settings.USERNAME_CHANGE_MAX_TIMES - self.n_times_changed_username,
                           's' if (settings.USERNAME_CHANGE_MAX_TIMES - self.n_times_changed_username) != 1 else '')
        else:
            help_text = "You already changed your username the maximum times allowed"
            self.fields['username'].disabled = True
        self.fields['username'].help_text += " " + help_text

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['username'].widget.attrs['placeholder'] = 'Write your name here (30 characters maximum)'
        self.fields['home_page'].widget.attrs['placeholder'] = 'Write a URL to show on your profile'
        self.fields['about'].widget.attrs['placeholder'] = 'Write something about yourself. ' \
                                                           'Note that this text will only appear in the profiles ' \
                                                           'of users who upload sounds.'
        self.fields['about'].widget.attrs['rows'] = False
        self.fields['about'].widget.attrs['cols'] = False
        self.fields['about'].widget.attrs['class'] = 'unsecure-image-check'
        self.fields['signature'].widget.attrs['placeholder'] = 'Write a signature for your forum messages'
        self.fields['signature'].widget.attrs['rows'] = False
        self.fields['signature'].widget.attrs['cols'] = False
        self.fields['signature'].widget.attrs['class'] = 'unsecure-image-check'
        self.fields['sound_signature'].widget.attrs['placeholder'] = "Write a signature for your sound descriptions"
        self.fields['sound_signature'].widget.attrs['rows'] = False
        self.fields['sound_signature'].widget.attrs['cols'] = False
        self.fields['sound_signature'].widget.attrs['class'] = 'unsecure-image-check'
        self.fields['is_adult'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['not_shown_in_online_users_list'].widget = forms.HiddenInput()

    def clean_username(self):
        username = self.cleaned_data["username"]

        # NOTE: we also check for the "username" form field not being disabled because once the user has changed
        # username the maximum number of times, the "username" field will be marked as disabled at form creation time.
        # If the field is disabled, then the form's cleaned_data for that field will contain the initial contents
        # of the field (i.e. the User username) regardless of whatever data form the HTML form is posted in the request.
        if self.fields["username"].disabled:
            return username

        # If user has accidentally cleared the field, treat it as unchanged
        if not username:
            username = self.request.user.username

        # If username was not changed, consider it valid
        if username.lower() == self.request.user.username.lower():
            return username

        # Check that username is not used by another user. Note that because when the maximum number of username
        # changes is reached, the "username" field of the ProfileForm is disabled and its contents won't change.
        # Therefore we will never reach this part of the clean_username function and there's no need to check for
        # the number of times the username was previously changed
        if not username_taken_by_other_user(username):
            return username
        raise forms.ValidationError("This username is already taken or has been in used in the past by another user")

    def clean_about(self):
        about = self.cleaned_data['about']
        if about and is_spam(self.request, about):
            raise forms.ValidationError("Your 'about' text was considered spam, please edit and resubmit")
        return about

    def clean_signature(self):
        signature = self.cleaned_data['signature']
        if signature and is_spam(self.request, signature):
            raise forms.ValidationError("Your signature was considered spam, please edit and resubmit")
        return signature

    def clean_sound_signature(self):
        sound_signature = self.cleaned_data['sound_signature']

        if len(sound_signature) > 256:
            raise forms.ValidationError("Your sound signature must not exceed 256 chars, please edit and resubmit")

        if sound_signature and is_spam(self.request, sound_signature):
            raise forms.ValidationError("Your sound signature was considered spam, please edit and resubmit")

        return sound_signature

    class Meta:
        model = Profile
        fields = ('username', 'home_page', 'about', 'signature', 'sound_signature', 'is_adult', 
            'allow_simultaneous_playback', 'prefer_spectrograms', 'ui_theme_preference' )

    def get_img_check_fields(self):
        """ Returns fields that should show JS notification for unsafe `img` sources links (http://) """
        return [self['about'], self['signature'], self['sound_signature']]


class EmailResetForm(forms.Form):
    email = forms.EmailField(label="New email address", max_length=254)
    password = forms.CharField(label="Your password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # Using init function to pass user variable so later we can perform check_password in clean_password function
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_password(self):
        if not self.user.check_password(self.cleaned_data["password"]):
            raise forms.ValidationError("Incorrect password.")
        return self.cleaned_data['password']


DELETE_CHOICES = [('only_user', mark_safe('<span>Delete only my user account information</span>')),
                  ('delete_sounds', mark_safe('<span>Delete my user account information, my sounds and packs</span>'))]


class DeleteUserForm(forms.Form):
    encrypted_link = forms.CharField(widget=forms.HiddenInput())
    delete_sounds = forms.ChoiceField(label=False,  choices=DELETE_CHOICES, widget=forms.RadioSelect())
    password = forms.CharField(label="Confirm your password", widget=forms.PasswordInput)

    def clean_password(self):
        user = User.objects.get(id=self.user_id)
        if not user.check_password(self.cleaned_data["password"]):
            raise forms.ValidationError("Incorrect password.")
        return None

    def clean(self):
        data = self.cleaned_data['encrypted_link']
        if not data:
            raise PermissionDenied
        try:
            user_id = unsign_with_timestamp(str(self.user_id), data, max_age=10)
        except SignatureExpired:
            raise forms.ValidationError("Sorry, you waited too long, ... try again?")
        except BadSignature:
            raise PermissionDenied
        user_id = int(user_id)
        if user_id != self.user_id:
            raise PermissionDenied

    def reset_encrypted_link(self, user_id):
        self.data = self.data.copy()
        self.data["encrypted_link"] = sign_with_timestamp(user_id)

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id')
        encrypted_link = sign_with_timestamp(self.user_id)
        kwargs['initial'] = {
                'delete_sounds': 'only_user',
                'encrypted_link': encrypted_link
                }
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        # NOTE: the line below will add 'bw-radio' to all individual radio elements of
        # forms.RadioSelect but also to the main ul element that wraps them all. This is not
        # ideal as 'bw-radio' should only be applied to the radio elements. To solve this issue, the
        # CSS and JS for checkboxes has been updated to only apply to radio elements.
        self.fields['delete_sounds'].widget.attrs['class'] = 'bw-radio'


class EmailSettingsForm(forms.Form):
    email_types = forms.ModelMultipleChoiceField(
        queryset=EmailPreferenceType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: the line below will add 'bw-checkbox' to all individual checkbox elements of
        # forms.CheckboxSelectMultiple but also to the main ul element that wraps them all. This is not
        # ideal as 'bw-checkbox' should only be applied to the checkbox elements. To solve this issue, the
        # CSS and JS for checkboxes has been updated to only apply to checkbox elements.
        self.fields['email_types'].widget.attrs['class'] = 'bw-checkbox'


class FsPasswordResetForm(forms.Form):
    """
    This form is a modification of django's PasswordResetForm. The only difference is that here we allow the user
    to enter an email or a username (instead of only a username) to send the reset password email.
    Methods `send_email` and `save` are very similar to the original methods from
    `django.contrib.auth.forms.PasswordResetForm`. We could not inherit from the original form because we don't want
    the old `username` field to be present. When migrating to a new version of django (current is 1.11) we should check
    for updates in this code in case we also have to apply them.
    """
    username_or_email = forms.CharField(label="Email or Username", max_length=254)

    def get_users(self, username_or_email):
        """Given an email, return matching user(s) who should receive a reset.

            This subclass will let all active users reset their password.
            Django's PasswordReset form will only let a user reset their
            password if the password is "valid" (i.e., it's using a
            password hash that django understands)
        """
        UserModel = get_user_model()
        active_users = UserModel._default_manager.filter(Q(**{
                f'{UserModel.get_email_field_name()}__iexact': username_or_email,
                'is_active': True,
            }) | Q(**{
                'username__iexact': username_or_email,
                'is_active': True,
            })
        )
        return (u for u in active_users)

    def save(self, domain_override=None,
             subject_template_name='emails/password_reset_subject.txt',
             email_template_name='emails/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        username_or_email = self.cleaned_data["username_or_email"]
        for user in self.get_users(username_or_email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            if extra_email_context is not None:
                context.update(extra_email_context)
            dj_auth_form = PasswordResetForm()
            dj_auth_form.send_mail(
                subject_template_name, email_template_name, context, from_email,
                user.email, html_email_template_name=html_email_template_name,
            )


class FsSetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['new_password1'].label = False
        self.fields['new_password1'].help_text = False
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New password'
        self.fields['new_password2'].label = False
        self.fields['new_password2'].help_text = False
        self.fields['new_password2'].widget.attrs['placeholder'] = 'New password confirmation'


class FsPasswordChangeForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)
