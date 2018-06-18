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
from utils.forms import HtmlCleaningCharField
from utils.spam import is_spam

class PostReplyForm(forms.Form):
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=20)))
    subscribe = forms.BooleanField(help_text="Send me an email notification when new posts are added in this thread.", required=False, initial=True)
    def __init__(self, request, quote, *args, **kwargs):
        self.request = request
        self.quote = quote
        super(PostReplyForm, self).__init__(*args, **kwargs)

    def clean_body(self):
        body = self.cleaned_data['body']

        if self.quote and body.strip() == self.quote:
            raise forms.ValidationError("You should type something...")

        if is_spam(self.request, body):
            raise forms.ValidationError("Your post was considered spam, please edit and repost. If it keeps failing please contact the admins.")

        return body


class NewThreadForm(forms.Form):
    title = forms.CharField(max_length=250)
    body = HtmlCleaningCharField(widget=forms.Textarea(attrs=dict(cols=100, rows=30)))
    subscribe = forms.BooleanField(help_text="Send me an email notification when new posts are added in this thread.", required=False, initial=True)


MODERATION_CHOICES = [(x, x) for x in
                      ['Approve',
                       'Delete User',
                       'Delete Post']]


class PostModerationForm(forms.Form):
    action = forms.ChoiceField(choices=MODERATION_CHOICES,
                               required=True,
                               widget=forms.RadioSelect(),
                               label='')
    post = forms.IntegerField(widget=forms.widgets.HiddenInput)
