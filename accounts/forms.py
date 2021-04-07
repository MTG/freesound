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
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from multiupload.fields import MultiFileField
from django.conf import settings
from accounts.models import Profile, EmailPreferenceType, OldUsername
from utils.forms import HtmlCleaningCharField, filename_has_valid_extension, CaptchaWidget
from utils.spam import is_spam
from utils.encryption import decrypt, encrypt
import logging

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
                    # Firefox seems to set wrong mime type for ogg files to video/ogg instead of audio/ogg
                    # For this reason we also allow this mime type for ogg files.
                    if not content_type.startswith("audio") and not content_type == 'video/ogg':
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


def get_user_by_email(email):
    return User.objects.get(email__iexact=email)


class UsernameField(forms.CharField):
    """ Username field, 3~30 characters, allows only alphanumeric chars, required by default """
    def __init__(self, required=True):
        super(UsernameField, self).__init__(
            label="Username",
            min_length=3,
            max_length=30,
            validators=[RegexValidator(r'^[\w.+-]+$')],  # is the same as Django UsernameValidator except for '@' symbol
            help_text="30 characters or fewer. Can contain: letters, digits, underscores, dots, dashes and plus signs.",
            error_messages={'invalid': "This value must contain only letters, digits, underscores, dots, dashes and "
                                       "plus signs."},
            required=required)


class RegistrationForm(forms.Form):
    recaptcha_response = forms.CharField(widget=CaptchaWidget, required=False)
    username = UsernameField()

    email1 = forms.EmailField(label="Email", help_text="We will send you a confirmation/activation email, so make "
                                                       "sure this is correct!.", max_length=254)
    email2 = forms.EmailField(label="Email confirmation", help_text="Confirm your email address", max_length=254)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    accepted_tos = forms.BooleanField(
        label=mark_safe('Check this box to accept the <a href="/help/tos_web/" target="_blank">terms of use</a> of the '
                        'Freesound website'),
        required=True,
        error_messages={'required': 'You must accept the terms of use in order to register to Freesound'}
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            try:
                OldUsername.objects.get(username__iexact=username)
            except OldUsername.DoesNotExist:
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
        cleaned_data = super(RegistrationForm, self).clean()
        if settings.RECAPTCHA_PUBLIC_KEY:
            # If captcha is enabled, check that captcha is ok
            captcha_response = cleaned_data.get("recaptcha_response")
            if not captcha_response:
                raise forms.ValidationError({"recaptcha_response": "Captcha is not correct"})
        return cleaned_data

    def save(self):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email1"]
        password = self.cleaned_data["password1"]
        accepted_tos = self.cleaned_data.get("accepted_tos", False)

        user = User(username=username,
                    email=email,
                    is_staff=False,
                    is_active=False,
                    is_superuser=False)
        user.set_password(password)
        user.save()

        profile = user.profile  # .profile created on User.save()
        profile.accepted_tos = accepted_tos
        profile.save()

        return user


class BwRegistrationForm(RegistrationForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super(BwRegistrationForm, self).__init__(*args, **kwargs)

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['username'].label = False
        self.fields['username'].help_text = False
        self.fields['username'].widget.attrs['placeholder'] = 'Username (30 characters maximum)'
        self.fields['email1'].label = False
        self.fields['email1'].help_text = False
        self.fields['email1'].widget.attrs['placeholder'] = 'Email'
        self.fields['email2'].label = False
        self.fields['email2'].help_text = False
        self.fields['email2'].widget.attrs['placeholder'] = 'Email confirmation'
        self.fields['password1'].label = False
        self.fields['password1'].help_text = False
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['accepted_tos'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['accepted_tos'].label = mark_safe('Check this box to accept our <a href="/help/tos_web/" '
                                                      'target="_blank">terms of use</a>')


class ReactivationForm(forms.Form):
    user = forms.CharField(label="The username or email you signed up with", max_length=254)


class BwProblemsLoggingInForm(forms.Form):
    username_or_email = forms.CharField(label="", help_text="", max_length=254)

    def __init__(self, *args, **kwargs):
        super(BwProblemsLoggingInForm, self).__init__(*args, **kwargs)
        self.fields['username_or_email'].widget.attrs['placeholder'] = 'Your email or username'


class FsAuthenticationForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super(FsAuthenticationForm, self).__init__(*args, **kwargs)
        self.error_messages.update({
            'inactive': mark_safe("You are trying to log in with an inactive account, please <a href=\"%s\">activate "
                                  "your account</a> first." % reverse("accounts-resend-activation")),
            'invalid_login': "Please enter a correct username/email and password. "
                             "Note that passwords are case-sensitive.",
        })
        self.fields['username'].label = 'Username or email'


class BwFsAuthenticationForm(FsAuthenticationForm):

    def __init__(self, *args, **kwargs):
        super(BwFsAuthenticationForm, self).__init__(*args, **kwargs)

        # Customize form placeholders and remove labels
        self.fields['username'].label = False
        self.fields['username'].widget.attrs['placeholder'] = 'Enter your email or username'
        self.fields['password'].label = False
        self.fields['password'].widget.attrs['placeholder'] = 'Enter your password'


class UsernameReminderForm(forms.Form):
    user = forms.EmailField(label="The email address you signed up with", max_length=254)


class ProfileForm(forms.ModelForm):

    username = UsernameField(required=False)
    about = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(rows=20, cols=70)), required=False)
    signature = HtmlCleaningCharField(
        label="Forum signature",
        widget=forms.Textarea(attrs=dict(rows=10, cols=70)),
        required=False,
        max_length=256,
    )
    sound_signature = HtmlCleaningCharField(
        label="Sound signature",
        widget=forms.Textarea(attrs=dict(rows=10, cols=70)),
        help_text="""Your sound signature is added to the end of the description of all of your sounds.
                     You can use it to show a common message on all of your sounds. If you change the
                     sound signature it will be automatically updated on all of your sounds. Use the
                     special text <code>${sound_url}</code> to refer to the URL of the current sound being displayed
                     and <code>${sound_id}</code> to refer to the id of the current sound.""",
        required=False,
        max_length=256,
    )
    is_adult = forms.BooleanField(help_text="I'm an adult, I don't want to see inappropriate content warnings",
                                  label="", required=False)
    not_shown_in_online_users_list = forms.BooleanField(
        help_text="Hide from \"users currently online\" list in the People page",
        label="",
        required=False
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        kwargs.update(initial={
            'username': request.user.username
        })
        super(ProfileForm, self).__init__(*args, **kwargs)

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

    def clean_username(self):
        username = self.cleaned_data["username"]

        # If user has accidentally cleared the field, treat it as unchanged
        if not username:
            username = self.request.user.username

        # Check that:
        #   1) It is not taken by another user
        #   2) It was not used in the past by another (or the same) user
        #   3) It has not been changed the maximum number of allowed times
        # Only if the three conditions are met we allow to change the username
        try:
            User.objects.exclude(pk=self.request.user.id).get(username__iexact=username)
        except User.DoesNotExist:
            try:
                OldUsername.objects.get(username__iexact=username)
            except OldUsername.DoesNotExist:
                if self.n_times_changed_username >= settings.USERNAME_CHANGE_MAX_TIMES:
                    raise forms.ValidationError("Your username can't be changed any further. Please contact support "
                                                "if you still need to change it.")
                return username
        raise forms.ValidationError("This username is already taken or has been in used in the past")

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
        fields = ('home_page', 'about', 'signature', 'sound_signature', 'is_adult', 'not_shown_in_online_users_list', )

    def get_img_check_fields(self):
        """ Returns fields that should show JS notification for unsafe `img` sources links (http://) """
        return [self['about'], self['signature'], self['sound_signature']]


class BwProfileForm(ProfileForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super(BwProfileForm, self).__init__(*args, **kwargs)

        html_tags_help_text = """Allowed HTML tags: <code>a</code>, <code>img</code>, <code>strong</code>,
                <code>b</code>, <code>em</code>, <code>li</code>, <code>u</code>, <code>p</code>, <code>br</code>,
                <code>blockquote</code> and <code>code</code>."""

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['username'].widget.attrs['placeholder'] = 'Write your name here (30 characters maximum)'
        self.fields['home_page'].widget.attrs['placeholder'] = 'Write a URL to show on your profile'
        self.fields['about'].widget.attrs['placeholder'] = 'Write something about yourself'
        self.fields['about'].widget.attrs['rows'] = False
        self.fields['about'].widget.attrs['cols'] = False
        self.fields['about'].help_text = html_tags_help_text
        self.fields['signature'].widget.attrs['placeholder'] = 'Write a signature for your forum messages'
        self.fields['signature'].widget.attrs['rows'] = False
        self.fields['signature'].widget.attrs['cols'] = False
        self.fields['signature'].help_text = html_tags_help_text
        self.fields['sound_signature'].widget.attrs['placeholder'] = "Write a signature for your sound descriptions"
        self.fields['sound_signature'].widget.attrs['rows'] = False
        self.fields['sound_signature'].widget.attrs['cols'] = False
        self.fields['sound_signature'].help_text = """Your sound signature is added to the end of each of your sound 
            descriptions. If you change the sound signature it will be automatically updated on all of your sounds. 
            Use the special text <code>${sound_url}</code> to refer to the URL of the current sound being displayed 
            and <code>${sound_id}</code> to refer to the id of the current sound. """ + html_tags_help_text

        self.fields['is_adult'].widget.attrs['class'] = 'bw-checkbox'
        self.fields['is_adult'].label = self.fields['is_adult'].help_text
        self.fields['is_adult'].help_text = False
        self.fields['not_shown_in_online_users_list'].widget = forms.HiddenInput()

    class Meta:
        model = Profile
        fields = ('username', 'home_page', 'about', 'signature', 'sound_signature', 'is_adult', )


class EmailResetForm(forms.Form):
    email = forms.EmailField(label="New email address", max_length=254)
    password = forms.CharField(label="Your password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # Using init function to pass user variable so later we can perform check_password in clean_password function
        self.user = kwargs.pop('user', None)
        super(EmailResetForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        if not self.user.check_password(self.cleaned_data["password"]):
            raise forms.ValidationError("Incorrect password.")
        return self.cleaned_data['password']


DELETE_CHOICES = [('only_user',
                   mark_safe(u'Delete only my user account information :)  '
                             u'(see <a href="/help/faq/#how-do-i-delete-myself-from-your-site" target="_blank">here</a>'
                             u' for more information)')),
                  ('delete_sounds', u'Delete also my sounds and packs :(')]


class DeleteUserForm(forms.Form):
    encrypted_link = forms.CharField(widget=forms.HiddenInput())
    delete_sounds = forms.ChoiceField(choices=DELETE_CHOICES, widget=forms.RadioSelect())
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
        user_id, now = decrypt(data).split("\t")
        user_id = int(user_id)
        if user_id != self.user_id:
            raise PermissionDenied
        link_generated_time = float(now)
        if abs(time.time() - link_generated_time) > 10:
            raise forms.ValidationError("Sorry, you waited too long, ... try again?")

    def reset_encrypted_link(self, user_id):
        self.data = self.data.copy()
        self.data["encrypted_link"] = encrypt(u"%d\t%f" % (user_id, time.time()))

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id')
        encrypted_link = encrypt(u"%d\t%f" % (self.user_id, time.time()))
        kwargs['initial'] = {
                'delete_sounds': 'only_user',
                'encrypted_link': encrypted_link
                }
        super(DeleteUserForm, self).__init__(*args, **kwargs)


class EmailSettingsForm(forms.Form):
    email_types = forms.ModelMultipleChoiceField(
        queryset=EmailPreferenceType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select the events for which you want to be notified by email:'
    )

class BwEmailSettingsForm(EmailSettingsForm):

    def __init__(self, *args, **kwargs):
        super(BwEmailSettingsForm, self).__init__(*args, **kwargs)
        self.fields['email_types'].label = False
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
                '%s__iexact' % UserModel.get_email_field_name(): username_or_email,
                'is_active': True,
            }) | Q(**{
                'username__iexact': username_or_email,
                'is_active': True,
            })
        )
        return (u for u in active_users)

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
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


class BwSetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super(BwSetPasswordForm, self).__init__(*args, **kwargs)

        # Customize some placeholders and classes, remove labels and help texts
        self.fields['new_password1'].label = False
        self.fields['new_password1'].help_text = False
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New password'
        self.fields['new_password2'].label = False
        self.fields['new_password2'].help_text = False
        self.fields['new_password2'].widget.attrs['placeholder'] = 'New password confirmation'
