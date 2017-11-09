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

from django.test import TestCase, Client

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
import sounds
import ratings

class RatingsTestCase(TestCase):

    fixtures = ['sounds']

    def setUp(self):
        self.sound = sounds.models.Sound.objects.get(pk=16)
        self.ct = ContentType.objects.get_for_model(sounds.models.Sound)
        self.user1 = User.objects.create_user("testuser1", email="testuser1@freesound.org", password="testpass")
        self.user2 = User.objects.create_user("testuser2", email="testuser2@freesound.org", password="testpass")

    def test_rating_normal(self):
        """ Add a rating """
        self.assertEqual(self.sound.num_ratings, 0)
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)
        # One rating from a different user
        r = ratings.models.Rating.objects.create(object_id=self.sound.id, content_type=self.ct, user_id=self.user2.id, rating=2)

        # Test signal updated sound.avg_rating
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 2.0)
        self.assertEqual(self.sound.num_ratings, 1)

        RATING_VALUE = 3
        resp = self.client.get("/ratings/add/%s/%s/%s/" % (self.ct.id, self.sound.id, RATING_VALUE))
        self.assertEqual(resp.content, "2")

        self.assertEqual(ratings.models.Rating.objects.count(), 2)
        r = ratings.models.Rating.objects.get(object_id=self.sound.id, content_type=self.ct, user_id=self.user1.id)
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
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)

        r = ratings.models.Rating.objects.create(object_id=self.sound.id, content_type=self.ct, user_id=self.user1.id, rating=4)

        resp = self.client.get("/ratings/add/%s/%s/%s/" % (self.ct.id, self.sound.id, 5))
        newr = ratings.models.Rating.objects.first()
        self.assertEqual(ratings.models.Rating.objects.count(), 1)
        # Ratings in the database are 2x the value from the web call
        self.assertEqual(newr.rating, 10)

        # Check that signal updated sound.avg_rating. Number of ratings is still the same
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.avg_rating, 10.0)
        self.assertEqual(self.sound.num_ratings, 1)

    def test_rating_out_of_range(self):
        """ Change rating by a value which is not 1-5. """
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)

        resp = self.client.get("/ratings/add/%s/%s/%s/" % (self.ct.id, self.sound.id, 0))
        # After doing an invalid rating, there are still none for this sound
        self.assertEqual(resp.content, "0")

    def test_delete_all_ratings(self):
        r = ratings.models.Rating.objects.create(object_id=self.sound.id, content_type=self.ct, user_id=self.user2.id, rating=2)
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.num_ratings, 1)
        r.delete()
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.num_ratings, 0)
