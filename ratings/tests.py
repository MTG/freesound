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

from django.contrib.auth.models import User
from django.db.models import Max
from django.test import TestCase

import ratings.models
import sounds.models


class RatingsTestCase(TestCase):

    fixtures = ['licenses', 'sounds']

    def setUp(self):
        self.sound = sounds.models.Sound.objects.get(pk=16)
        self.user1 = User.objects.create_user("testuser1", email="testuser1@freesound.org", password="testpass")
        self.user2 = User.objects.create_user("testuser2", email="testuser2@freesound.org", password="testpass")

    def test_rating_normal(self):
        """ Add a rating """
        self.assertEqual(self.sound.num_ratings, 0)
        self.client.force_login(self.user1)

        # One rating from a different user
        r = ratings.models.SoundRating.objects.create(sound_id=self.sound.id, user_id=self.user2.id, rating=2)

        # Test signal updated sound.avg_rating
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 2.0)
        self.assertEqual(self.sound.num_ratings, 1)

        RATING_VALUE = 3
        resp = self.client.get("/people/Anton/sounds/%s/rate/%s/" % (self.sound.id, RATING_VALUE))
        self.assertEqual(resp.content, "2")

        self.assertEqual(ratings.models.SoundRating.objects.count(), 2)
        r = ratings.models.SoundRating.objects.get(sound_id=self.sound.id, user_id=self.user1.id)
        # Ratings in the database are 2x the value from the web call
        self.assertEqual(r.rating, 2*RATING_VALUE)

        # Check that signal updated sound.avg_rating and sound.num_ratings
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 4.0)
        self.assertEqual(self.sound.num_ratings, 2)

        # Delete one rating and check if signal updated avg_rating and num_ratings
        r.delete()
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 2.0)
        self.assertEqual(self.sound.num_ratings, 1)

    def test_rating_change(self):
        """ Change your existing rating. """
        self.client.force_login(self.user1)

        r = ratings.models.SoundRating.objects.create(sound_id=self.sound.id, user_id=self.user1.id, rating=4)

        resp = self.client.get("/people/Anton/sounds/%s/rate/%s/" % (self.sound.id, 5))
        newr = ratings.models.SoundRating.objects.first()
        self.assertEqual(ratings.models.SoundRating.objects.count(), 1)
        # Ratings in the database are 2x the value from the web call
        self.assertEqual(newr.rating, 10)

        # Check that signal updated sound.avg_rating. Number of ratings is still the same
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 10.0)
        self.assertEqual(self.sound.num_ratings, 1)

    def test_rating_out_of_range(self):
        """ Change rating by a value which is not 1-5. """
        self.client.force_login(self.user1)

        resp = self.client.get("/people/Anton/sounds/%s/rate/%s/" % (self.sound.id, 0))
        # After doing an invalid rating, there are still none for this sound
        self.assertEqual(resp.content, "0")

        resp = self.client.get("/people/Anton/sounds/%s/rate/%s/" % (self.sound.id, 6))
        self.assertEqual(resp.content, "0")

    def test_delete_all_ratings(self):
        r = ratings.models.SoundRating.objects.create(sound=self.sound, user_id=self.user2.id, rating=2)
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.num_ratings, 1)
        r.delete()
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.num_ratings, 0)

    def test_rating_no_sound(self):
        """Test behaviour if the sound id doesn't exist"""
        max_id = sounds.models.Sound.objects.all().aggregate(Max('id'))
        max_id = max_id['id__max']
        no_id = max_id + 20

        self.client.force_login(self.user1)

        resp = self.client.get("/people/Anton/sounds/%s/rate/%s/" % (no_id, 2))
        self.assertEqual(resp.status_code, 404)

        # If sound id doesn't match username
        resp = self.client.get("/people/NotAnton/sounds/%s/rate/%s/" % (self.sound.id, 2))
        self.assertEqual(resp.status_code, 404)


class RatingsPageTestCase(TestCase):

    fixtures = ['licenses', 'sounds', 'moderation_groups']

    def setUp(self):
        self.sound = sounds.models.Sound.objects.get(pk=16)
        self.user1 = User.objects.create_user("testuser1", email="testuser1@freesound.org", password="testpass")

    def test_rating_link_logged_in(self):
        """A logged in user viewing a sound should get links to rate the sound"""

        self.client.force_login(self.user1)
        resp = self.client.get(self.sound.get_absolute_url())
        self.assertContains(resp, '<a href="/people/Anton/sounds/%s/rate/1/" title="pretty bad :-(" class="one-star">' % self.sound.id)

    def test_no_rating_link_logged_out(self):
        """A logged out user doesn't see links to rate a sound"""
        resp = self.client.get(self.sound.get_absolute_url())
        self.assertNotContains(resp, '<a href="/people/Anton/sounds/%s/rate/1/" title="pretty bad :-(" class="one-star">' % self.sound.id)

    def test_no_rating_link_own_sound(self):
        """A user doesn't see links to rate their own sound"""
        user = User.objects.get(username="Anton")
        self.client.force_login(user)
        resp = self.client.get(self.sound.get_absolute_url())
        self.assertNotContains(resp, '<a href="/people/Anton/sounds/%s/rate/1/" title="pretty bad :-(" class="one-star">' % self.sound.id)
