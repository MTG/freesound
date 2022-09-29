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
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from utils.forms import CaptchaWidget, HtmlCleaningCharField
from utils.spam import is_spam


class ManualUserField(forms.CharField):
    def clean(self, value):
        if not value:
            raise forms.ValidationError('Please enter a username.')
        try:
            return User.objects.get(username__iexact=value)
        except User.DoesNotExist:  # @UndefinedVariable
            raise forms.ValidationError("We are sorry, but this username does not exist...")


class MessageReplyForm(forms.Form):
    to = ManualUserField(widget=forms.TextInput(attrs={'size': '40'}))
    subject = forms.CharField(min_length=3, max_length=128, widget=forms.TextInput(attrs={'size': '80'}))
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))

    def __init__(self, request, *args, **kwargs):
        self.request = request  # This is used by MessageReplyFormWithCaptcha to be able to call is_spam function
        super(MessageReplyForm, self).__init__(*args, **kwargs)


class MessageReplyFormWithCaptcha(MessageReplyForm):
    recaptcha_response = forms.CharField(widget=CaptchaWidget, required=False)

    def clean_recaptcha_response(self):
        captcha_response = self.cleaned_data.get("recaptcha_response")
        if settings.RECAPTCHA_PUBLIC_KEY:
            if not captcha_response:
                raise forms.ValidationError("Captcha is not correct")
        return captcha_response

    def clean_body(self):
        body = self.cleaned_data['body']
        if is_spam(self.request, body):
            raise forms.ValidationError("Your message was considered spam. If your message is not spam and the "
                                        "check keeps failing, please contact the admins.")
        return body


class BwMessageReplyForm(MessageReplyForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super(BwMessageReplyForm, self).__init__(*args, **kwargs)

        html_tags_help_text = """Allowed HTML tags: <code>a</code>, <code>img</code>, <code>strong</code>,
                    <code>b</code>, <code>em</code>, <code>li</code>, <code>u</code>, <code>p</code>, <code>br</code>,
                    <code>blockquote</code> and <code>code</code>."""

        self.fields['to'].widget.attrs['placeholder'] = "Username of the user to send the message to"
        self.fields['to'].widget.attrs['data-autocomplete-suggestions-url'] = reverse('messages-username_lookup')
        self.fields['to'].widget.attrs['data-check-username-url'] = reverse('check_username')
        self.fields['to'].widget.attrs['id'] = "username-to-field"
        self.fields['subject'].widget.attrs['placeholder'] = "Subject of your message, don't make it too long :)"
        self.fields['body'].widget.attrs['placeholder'] = "Write your message here"
        self.fields['body'].widget.attrs['rows'] = False
        self.fields['body'].widget.attrs['cols'] = False
        self.fields['body'].widget.attrs['class'] = 'unsecure-image-check'
        self.fields['body'].help_text = html_tags_help_text


class BwMessageReplyFormWithCaptcha(MessageReplyFormWithCaptcha):
    
    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super(BwMessageReplyFormWithCaptcha, self).__init__(*args, **kwargs)

        html_tags_help_text = """Allowed HTML tags: <code>a</code>, <code>img</code>, <code>strong</code>,
                    <code>b</code>, <code>em</code>, <code>li</code>, <code>u</code>, <code>p</code>, <code>br</code>,
                    <code>blockquote</code> and <code>code</code>."""

        self.fields['to'].widget.attrs['placeholder'] = "Username of the user to send the message to"
        self.fields['to'].widget.attrs['data-autocomplete-suggestions-url'] = reverse('messages-username_lookup')
        self.fields['to'].widget.attrs['data-check-username-url'] = reverse('check_username')
        self.fields['to'].widget.attrs['id'] = "username-to-field"
        self.fields['subject'].widget.attrs['placeholder'] = "Subject of your message, don't make it too long :)"
        self.fields['body'].widget.attrs['placeholder'] = "Write your message here"
        self.fields['body'].widget.attrs['rows'] = False
        self.fields['body'].widget.attrs['cols'] = False
        self.fields['body'].widget.attrs['class'] = 'unsecure-image-check'
        self.fields['body'].help_text = html_tags_help_text