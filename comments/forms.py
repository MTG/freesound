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


class CommentForm(forms.Form):
    comment = HtmlCleaningCharField(
        widget=forms.Textarea,
        max_length=4000,
        label='',
        help_text=
        "You can add comments with a timestamp using the syntax #minute:second (e.g., \"The sound in #1:34 is really neat\")."
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        self.fields['comment'].widget.attrs['placeholder'] = 'Write your comment here...'
        self.fields['comment'].widget.attrs['rows'] = False
        self.fields['comment'].widget.attrs['cols'] = False

    def clean_comment(self):
        comment = self.cleaned_data['comment']

        if is_spam(self.request, comment):
            raise forms.ValidationError(
                "Your comment was considered spam, please edit and repost. If it keeps failing please contact the admins."
            )

        return comment
