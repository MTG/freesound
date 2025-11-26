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
from django.test import TestCase

from comments.models import Comment
from utils.test_helpers import create_user_and_sounds


class CommentsWithHyperlinksTestCase(TestCase):
    """Tests for the pre/post save signals on Forum, Thread, and Post objects"""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, sounds = create_user_and_sounds(num_sounds=1)
        self.sound = sounds[0]

    def test_save_comment_with_hyperlinks(self):
        """Test that 'contains_hyperlink' boolean field is properly set when saving comments"""

        comment = Comment.objects.create(
            user=self.user, sound=self.sound, comment="This is a comment with no hyperlinks"
        )
        comment.refresh_from_db()
        self.assertFalse(comment.contains_hyperlink)

        comment = Comment.objects.create(
            user=self.user, sound=self.sound, comment="This is a comment with a link to http://www.freesound.org"
        )
        comment.refresh_from_db()
        self.assertTrue(comment.contains_hyperlink)

        comment = Comment.objects.create(
            user=self.user, sound=self.sound, comment="This is a comment with a https link to https://www.freesound.org"
        )
        comment.refresh_from_db()
        self.assertTrue(comment.contains_hyperlink)

    def test_update_comment_with_hyperlinks(self):
        """Test that 'contains_hyperlink' boolean field is properly set when updating comments"""

        comment = Comment.objects.create(
            user=self.user, sound=self.sound, comment="This is a comment with no hyperlinks"
        )
        comment.refresh_from_db()
        self.assertFalse(comment.contains_hyperlink)

        comment.comment = "Now this comment has a link to http://www.freesound.org"
        comment.save()
        comment.refresh_from_db()
        self.assertTrue(comment.contains_hyperlink)
