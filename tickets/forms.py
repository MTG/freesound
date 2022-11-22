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

from captcha.fields import ReCaptchaField
from django import forms
from django.utils.safestring import mark_safe

from utils.forms import HtmlCleaningCharField


class ModeratorMessageForm(forms.Form):
    message = HtmlCleaningCharField(widget=forms.Textarea)
    moderator_only = forms.BooleanField(required=False)


class UserMessageForm(forms.Form):
    message = HtmlCleaningCharField(widget=forms.Textarea)


class UserContactForm(UserMessageForm):
    title = HtmlCleaningCharField()

    def __init__(self, *args, **kwargs):
        super(UserContactForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['title', 'message']


class AnonymousMessageForm(forms.Form):
    message = HtmlCleaningCharField(widget=forms.Textarea)
    recaptcha = ReCaptchaField(label="")


class AnonymousContactForm(AnonymousMessageForm):
    title = HtmlCleaningCharField()
    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super(AnonymousContactForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'title', 'message']


# Sound moderation forms
MODERATION_CHOICES = [(x, x) for x in
                      ['Approve',
                       'Delete',
                       'Defer',
                       'Return',
                       'Whitelist']]

IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY = "K"
IS_EXPLICIT_ADD_FLAG_KEY = "A"
IS_EXPLICIT_REMOVE_FLAG_KEY = "R"
IS_EXPLICIT_FLAG_CHOICES = ((IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY, 'Keep user preference'),
                            (IS_EXPLICIT_ADD_FLAG_KEY, 'Add "is explicit" flag'),
                            (IS_EXPLICIT_REMOVE_FLAG_KEY, 'Remove "is explicit" flag'))


class SoundModerationForm(forms.Form):
    action = forms.ChoiceField(choices=MODERATION_CHOICES,
                               required=True,
                               widget=forms.RadioSelect(),
                               label='')

    ticket = forms.CharField(widget=forms.widgets.HiddenInput,
                             error_messages={'required': 'No sound selected...'})

    is_explicit = forms.ChoiceField(choices=IS_EXPLICIT_FLAG_CHOICES,
                                    initial=IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY,
                                    required=True,
                                    label=mark_safe("<i>Is explicit</i> flag"))


class ModerationMessageForm(forms.Form):
    message = HtmlCleaningCharField(widget=forms.Textarea,
                                    required=False,
                                    label='')
    moderator_only = forms.BooleanField(required=False)


class UserAnnotationForm(forms.Form):
    text = HtmlCleaningCharField(widget=forms.Textarea,
                                 required=True,
                                 label='')


class SoundStateForm(forms.Form):
    action = forms.ChoiceField(choices=MODERATION_CHOICES,
                               required=False,
                               label='Action:')
