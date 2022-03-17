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
import re

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError

from utils.text import clean_html, is_shouting
from django.conf import settings
from recaptcha.client import captcha
from urllib2 import URLError
from utils.tags import clean_and_split_tags
from HTMLParser import HTMLParseError


def filename_has_valid_extension(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1].lower() in settings.ALLOWED_AUDIOFILE_EXTENSIONS


class HtmlCleaningCharField(forms.CharField):
    """ A field that removes disallowed HTML tags as implemented in utils.text.clean_html and checks for
     too many upper chase characters"""
    def clean(self, value):
        value = super(HtmlCleaningCharField, self).clean(value)
        if is_shouting(value):
            raise forms.ValidationError('Please moderate the amount of upper case characters in your post...')
        return clean_html(value)


class TagField(forms.CharField):
    """ Gets the value of tags as a single string (with tags separated by spaces or commas) and cleans it to a set of
    unique tag strings """

    def __init__(self, **kwargs):
        super(TagField, self).__init__(**kwargs)
        self.validators.append(
            validators.MinLengthValidator(3, 'You should add at least 3 different tags. Tags must be separated by '
                                             'spaces'))
        self.validators.append(
            validators.MaxLengthValidator(30, 'There can be maximum 30 tags, please select the most relevant ones!'))

    def to_python(self, value):
        value = super(TagField, self).to_python(value)
        alphanum_only = re.compile(r"[^ a-zA-Z0-9-,]")
        if alphanum_only.search(value):
            raise ValidationError("Tags must contain only letters a-z, digits 0-9 and hyphen")
        return clean_and_split_tags(value)


class RecaptchaWidget(forms.Widget):
    """ A Widget which "renders" the output of captcha.displayhtml """
    def render(self, *args, **kwargs):
        if settings.RECAPTCHA_PUBLIC_KEY == '':
            return ''
        return captcha.displayhtml(settings.RECAPTCHA_PUBLIC_KEY).strip()


class RecaptchaWidgetSSL(forms.Widget):
    """ A Widget which "renders" the output of captcha.displayhtml using SSL option"""
    def render(self, *args, **kwargs):
        if settings.RECAPTCHA_PUBLIC_KEY == '':
            return ''
        return captcha.displayhtml(settings.RECAPTCHA_PUBLIC_KEY, use_ssl=True).strip()


class DummyWidget(forms.Widget):
    """
    A Widget class for captcha. Converts the recaptcha response field into a readable field for the form
    """

    # make sure that labels are not displayed either
    is_hidden = True

    recaptcha_response_field = 'g-recaptcha-response'

    def render(self, *args, **kwargs):
        return ''

    def value_from_datadict(self, data, files, name):
        return data.get(self.recaptcha_response_field, None)


class CaptchaWidget(forms.Widget):
    """
    A Widget class for captcha. Converts the recaptcha response field into a readable field for the form
    """

    # make sure that labels are not displayed either
    is_hidden = True

    recaptcha_response_field = 'g-recaptcha-response'

    def render(self, *args, **kwargs):
        return ''

    def value_from_datadict(self, data, files, name):
        return data.get(self.recaptcha_response_field, None)


class RecaptchaForm(forms.Form):
    """
    A form class which uses reCAPTCHA for user validation.
    If the captcha is not guessed correctly, a ValidationError is raised
    for the appropriate field
    """

    captcha_enabled = settings.RECAPTCHA_PUBLIC_KEY != ''

    recaptcha_challenge_field = forms.CharField(widget=DummyWidget, required=captcha_enabled)
    recaptcha_response_field = forms.CharField(widget=RecaptchaWidget, required=captcha_enabled, label="Please prove you are not a robot:")

    if not captcha_enabled:
        recaptcha_response_field.label = ''

    def __init__(self, request, *args, **kwargs):
        if request.is_secure():
            # If request is https present https form
            self.base_fields['recaptcha_response_field'].widget = RecaptchaWidgetSSL()

        super(RecaptchaForm, self).__init__(*args, **kwargs)
        self._request = request

        # move the captcha to the bottom of the list of fields
        recaptcha_fields = ['recaptcha_challenge_field', 'recaptcha_response_field']
        self.fields.keyOrder = [key for key in self.fields.keys() if key not in recaptcha_fields] + recaptcha_fields

    def clean_recaptcha_response_field(self):
        if 'recaptcha_challenge_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_response_field']

    def clean_recaptcha_challenge_field(self):
        if 'recaptcha_response_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_challenge_field']

    def validate_captcha(self):
        rcf = self.cleaned_data['recaptcha_challenge_field']
        rrf = self.cleaned_data['recaptcha_response_field']
        ip_address = self._request.META['REMOTE_ADDR']

        # only submit captcha information if it is enabled
        if self.captcha_enabled:
            try:
                check = captcha.submit(rcf, rrf, settings.RECAPTCHA_PRIVATE_KEY, ip_address)
                if not check.is_valid:
                    raise forms.ValidationError('You have not entered the correct words')
            except URLError as timeout:
                # We often sometimes see error messages that recaptcha url is unreachable and
                # this causes 500 errors. If recaptcha is unreachable, just skip captcha validation.
                pass
