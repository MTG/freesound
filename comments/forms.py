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
    comment = HtmlCleaningCharField(widget=forms.Textarea, max_length=4000)
    
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
    
    def clean_comment(self):
        comment = self.cleaned_data['comment']

        if is_spam(self.request, comment):
            raise forms.ValidationError("Your comment was considered spam, please edit and repost. If it keeps failing please contact the admins.")
        
        return comment


class BwCommentForm(CommentForm):

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(label_suffix=''))
        super().__init__(*args, **kwargs)

        self.fields['comment'].widget.attrs['placeholder'] = 'Write your comment here...'
        self.fields['comment'].widget.attrs['rows'] = False
        self.fields['comment'].widget.attrs['cols'] = False
        self.fields['comment'].label = ""
        self.fields['comment'].help_text = "You can refer to a specific second of the sound using the syntax #mm:ss (e.g., use #1:34 to refer to 1 minute and 23 seconds)."
        #self.fields['comment'].widget.attrs['class'] = 'unsecure-image-check'