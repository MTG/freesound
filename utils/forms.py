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
from utils.text import clean_html, is_shouting
from django.conf import settings
from recaptcha.client import captcha
from utils.tags import clean_and_split_tags
from HTMLParser import HTMLParseError


def filename_has_valid_extension(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1].lower() in settings.ALLOWED_AUDIOFILE_EXTENSIONS


class HtmlCleaningCharField(forms.CharField):
    def clean(self, value):
        value = super(HtmlCleaningCharField, self).clean(value)

        if is_shouting(value):
            raise forms.ValidationError('Please moderate the amount of upper case characters in your post...')
        try:
            return clean_html(value)
        except HTMLParseError:
            raise forms.ValidationError('The text you submitted is badly formed HTML, please fix it')


class TagField(forms.CharField):
    def clean(self, value):
        tags = clean_and_split_tags(value)

        if len(tags) < 3:
            raise forms.ValidationError('You should at least have 3 tags...')
        elif len(tags) > 30:
            raise forms.ValidationError('There can be maximum 30 tags, please select the most relevant ones!')

        return tags


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
