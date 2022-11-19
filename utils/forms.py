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
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError

from utils.tags import clean_and_split_tags
from utils.text import clean_html, is_shouting


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
