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
from wiki import models


class ContentForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={"size": "100"}), label=False)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": "40", "cols": "100"}), label=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["placeholder"] = "Title of the page"
        self.fields["body"].widget.attrs["placeholder"] = (
            "Contents of the page. You can use Markdown formatting and HTML."
        )

    class Meta:
        model = models.Content
        exclude = ("author", "page", "created")
