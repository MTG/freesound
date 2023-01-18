# -*- coding: utf-8 -*-
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
from builtins import range
from django.core.exceptions import ValidationError
from django.test import TestCase

from utils.forms import filename_has_valid_extension, TagField


class UtilsTest(TestCase):
    def test_filename_has_valid_extension(self):
        cases = [
            ("filaneme.wav", True),
            ("filaneme.aiff", True),
            ("filaneme.aif", True),
            ("filaneme.mp3", True),
            ("filaneme.ogg", True),
            ("filaneme.flac", True),
            ("filaneme.xyz", False),
            ("wav", False),
        ]
        for filename, expected_result in cases:
            self.assertEqual(filename_has_valid_extension(filename), expected_result)


class TagFieldTest(TestCase):
    def test_tag_field(self):
        f = TagField()
        # Split on spaces
        self.assertEqual({"One", "two2", "3three"}, f.clean("3three One two2"))
        
        # Split on commas
        self.assertEqual({"one", "two", "three"}, f.clean("three, one,two"))
        
        # Funny characters not allowed
        err_message = "Tags must contain only letters a-z, digits 0-9 and hyphen"
        with self.assertRaisesMessage(ValidationError, err_message):
            f.clean("One t%wo")
        
        # accents not allowed
        with self.assertRaisesMessage(ValidationError, err_message):
            f.clean("One twó")
        
        # hyphens allowed
        self.assertEqual({"tag", "tag-name", "another-name"}, f.clean("tag-name tag another-name"))
        
        # multiple hyphens cut down to one
        self.assertEqual({"tag", "tag-name", "another-name"}, f.clean("tag--name tag another----name"))

        # minimum number tags
        err_message = "You should add at least 3 different tags. Tags must be separated by spaces"
        with self.assertRaisesMessage(ValidationError, err_message):
            f.clean("One two")

        # maximum number tags
        err_message = "There can be maximum 30 tags, please select the most relevant ones!"
        with self.assertRaisesMessage(ValidationError, err_message):
            tags = " ".join(["tag%s" % i for i in range(35)])
            f.clean(tags)

        # remove common words
        self.assertEqual({"one", "two", "three"}, f.clean("three the of one to two one"))

        # duplicate tags removed
        self.assertEqual({"one", "two", "three"}, f.clean("three one two three one"))
