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

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from forum.models import Forum, Post, Thread
from ratings.models import SoundRating
from utils.test_helpers import create_user_and_sounds


class ReportCountStatusesManagementCommandTestCase(TestCase):
    fixtures = ["licenses"]

    def test_report_count_statuses(self):
        # Create some initial data
        user, pp, ss = create_user_and_sounds(num_sounds=1, num_packs=1)
        pack = pp[0]
        sound = ss[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        SoundRating.objects.create(sound=sound, user=user, rating=4)
        sound.refresh_from_db()  # Refresh from db after methods that use F-expressions
        sound.add_comment(user=user, comment="testComment")
        sound.refresh_from_db()  # Refresh from db after methods that use F-expressions
        forum = Forum.objects.create(name="testForum", name_slug="test_forum", description="test")
        thread = Thread.objects.create(forum=forum, title="testThread", author=user)
        Post.objects.create(author=user, body="testBody", thread=thread)
        Post.objects.create(author=user, body="testBody unmoderated", thread=thread, moderation_state="NM")
        user.profile.refresh_from_db()  # Refresh from db after methods that use F-expressions

        # Assert initial counts are ok
        self.assertEqual(user.profile.num_sounds, 1)
        self.assertEqual(user.profile.num_posts, 1)  # Note that count is 1 because one of the posts is not moderated
        self.assertEqual(pack.num_sounds, 1)
        self.assertEqual(pack.num_downloads, 0)
        self.assertEqual(sound.num_ratings, 1)
        self.assertEqual(sound.avg_rating, 4)
        self.assertEqual(sound.num_comments, 1)
        self.assertEqual(sound.num_downloads, 0)

        # Run command and assert counts are still ok
        call_command("report_count_statuses")
        self.assertEqual(user.profile.num_sounds, 1)
        self.assertEqual(user.profile.num_posts, 1)
        self.assertEqual(pack.num_sounds, 1)
        self.assertEqual(pack.num_downloads, 0)
        self.assertEqual(sound.num_ratings, 1)
        self.assertEqual(sound.avg_rating, 4)
        self.assertEqual(sound.num_comments, 1)
        self.assertEqual(sound.num_downloads, 0)

        # Manually set the counts to something wrong
        user.profile.num_sounds = 21
        user.profile.num_posts = 21
        user.profile.save()
        pack.num_sounds = 21
        pack.num_downloads = 21
        pack.save()
        sound.num_ratings = 21
        sound.avg_rating = 21
        sound.num_comments = 21
        sound.num_downloads = 21
        sound.save()

        # Re-run command with -n and assert counts are still wrong
        call_command("report_count_statuses", "--no-changes")
        user.profile.refresh_from_db()
        sound.refresh_from_db()
        pack.refresh_from_db()
        self.assertNotEqual(user.profile.num_sounds, 1)
        self.assertNotEqual(user.profile.num_posts, 1)
        self.assertNotEqual(pack.num_sounds, 1)
        self.assertNotEqual(pack.num_downloads, 0)
        self.assertNotEqual(sound.num_ratings, 1)
        self.assertNotEqual(sound.avg_rating, 4)
        self.assertNotEqual(sound.num_comments, 1)
        self.assertNotEqual(sound.num_downloads, 0)

        # Re-run command with -d and assert that all counts are ok except for download counts
        call_command("report_count_statuses", "--skip-downloads")
        user.profile.refresh_from_db()
        sound.refresh_from_db()
        pack.refresh_from_db()
        self.assertEqual(user.profile.num_sounds, 1)
        self.assertEqual(user.profile.num_posts, 1)  # Note this is still 1 as unmoderated posts do not count
        self.assertEqual(pack.num_sounds, 1)
        self.assertNotEqual(pack.num_downloads, 0)
        self.assertEqual(sound.num_ratings, 1)
        self.assertEqual(sound.avg_rating, 4)
        self.assertEqual(sound.num_comments, 1)
        self.assertNotEqual(sound.num_downloads, 0)

        # Re-run command with no options set and check that all counts are ok now
        call_command("report_count_statuses")
        user.profile.refresh_from_db()
        sound.refresh_from_db()
        pack.refresh_from_db()
        self.assertEqual(user.profile.num_sounds, 1)
        self.assertEqual(user.profile.num_posts, 1)
        self.assertEqual(pack.num_sounds, 1)
        self.assertEqual(pack.num_downloads, 0)
        self.assertEqual(sound.num_ratings, 1)
        self.assertEqual(sound.avg_rating, 4)
        self.assertEqual(sound.num_comments, 1)
        self.assertEqual(sound.num_downloads, 0)
