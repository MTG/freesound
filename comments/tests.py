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
import pytest

from comments.models import Comment
from utils.test_helpers import create_user_and_sounds


@pytest.fixture
def comment_author_and_sound(load_fixtures):
    load_fixtures(["licenses"])
    user, _, sounds = create_user_and_sounds(num_sounds=1)
    return user, sounds[0]


def test_save_comment_with_hyperlinks(comment_author_and_sound):
    """Test that 'contains_hyperlink' boolean field is properly set when saving comments"""
    user, sound = comment_author_and_sound

    comment = Comment.objects.create(user=user, sound=sound, comment="This is a comment with no hyperlinks")
    comment.refresh_from_db()
    assert not comment.contains_hyperlink

    comment = Comment.objects.create(
        user=user, sound=sound, comment="This is a comment with a link to http://www.freesound.org"
    )
    comment.refresh_from_db()
    assert comment.contains_hyperlink

    comment = Comment.objects.create(
        user=user, sound=sound, comment="This is a comment with a https link to https://www.freesound.org"
    )
    comment.refresh_from_db()
    assert comment.contains_hyperlink


def test_update_comment_with_hyperlinks(comment_author_and_sound):
    """Test that 'contains_hyperlink' boolean field is properly set when updating comments"""
    user, sound = comment_author_and_sound

    comment = Comment.objects.create(user=user, sound=sound, comment="This is a comment with no hyperlinks")
    comment.refresh_from_db()
    assert not comment.contains_hyperlink

    comment.comment = "Now this comment has a link to http://www.freesound.org"
    comment.save()
    comment.refresh_from_db()
    assert comment.contains_hyperlink
