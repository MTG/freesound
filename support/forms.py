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
from utils.forms import CaptchaWidget


class ContactForm(forms.Form):
    your_email = forms.EmailField()
    subject = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 10, 'cols': 50}))
    recaptcha_response = forms.CharField(widget=CaptchaWidget)

    def clean_recaptcha_response(self):
        captcha_response = self.cleaned_data.get("recaptcha_response")
        if settings.RECAPTCHA_PUBLIC_KEY:
            if not captcha_response:
                raise forms.ValidationError(_("Captcha is not correct"))
        return captcha_response

