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

from django_recaptcha.fields import ReCaptchaField
from django import forms
from django.contrib.auth.models import User
from django.urls import reverse

from utils.forms import HtmlCleaningCharField
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
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)), 
                                 help_text=HtmlCleaningCharField.make_help_text())

    def __init__(self, request, *args, **kwargs):
        self.request = request  # This is used by MessageReplyFormWithCaptcha to be able to call is_spam function
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        self.fields['to'].widget.attrs['placeholder'] = "Username of the user to send the message to"
        self.fields['to'].widget.attrs['data-typeahead'] = 'true' 
        self.fields['to'].widget.attrs['data-typeahead-suggestions-url'] = reverse('messages-username_lookup')
        self.fields['to'].widget.attrs['data-check-username-url'] = reverse('check_username')
        self.fields['to'].widget.attrs['id'] = "username-to-field"
        self.fields['to'].widget.attrs['autocomplete'] = "off"
        self.fields['subject'].widget.attrs['placeholder'] = "Subject of your message, don't make it too long :)"
        self.fields['body'].widget.attrs['placeholder'] = "Write your message here"
        self.fields['body'].widget.attrs['rows'] = False
        self.fields['body'].widget.attrs['cols'] = False
        self.fields['body'].widget.attrs['class'] = 'unsecure-image-check'


class MessageReplyFormWithCaptcha(MessageReplyForm):
    recaptcha = ReCaptchaField(label="")

    def clean_body(self):
        body = self.cleaned_data['body']
        if is_spam(self.request, body):
            raise forms.ValidationError("Your message was considered spam. If your message is not spam and the "
                                        "check keeps failing, please contact the admins.")
        return body
