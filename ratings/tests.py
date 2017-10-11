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
        self.sound = sounds.models.Sound.objects.all()[0]
        self.user1 = User.objects.create_user("testuser1", email="testuser1@freesound.org", password="testpass")
        self.user2 = User.objects.create_user("testuser2", email="testuser2@freesound.org", password="testpass")

    def test_rating_normal(self):
        """ Add a rating """
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)
        # One rating from a different user
        r = ratings.models.Rating.objects.create(sound_id=self.sound.id, user_id=self.user2.id, rating=2)

        resp = self.client.get("/ratings/add/%s/%s/" % (self.sound.id, 3))
        self.assertEqual(resp.content, "2")

        self.assertEqual(ratings.models.Rating.objects.count(), 2)
        r = ratings.models.Rating.objects.get(sound_id=self.sound.id, user_id=self.user1.id)
        # Ratings in the database are 2x the value from the web call
        self.assertEqual(r.rating, 6)

    def test_rating_change(self):
        """ Change your existing rating. """
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)

        r = ratings.models.Rating.objects.create(sound_id=self.sound.id, user_id=self.user1.id, rating=4)

        resp = self.client.get("/ratings/add/%s/%s/" % (self.sound.id, 5))
        newr = ratings.models.Rating.objects.first()
        self.assertEqual(ratings.models.Rating.objects.count(), 1)
        # Ratings in the database are 2x the value from the web call
        self.assertEqual(newr.rating, 10)

    def test_rating_out_of_range(self):
        """ Change rating by a value which is not 1-5. """
        loggedin = self.client.login(username="testuser1", password="testpass")
        self.assertTrue(loggedin)

        resp = self.client.get("/ratings/add/%s/%s/" % (self.sound.id, 0))
        # After doing an invalid rating, there are still none for this sound
        self.assertEqual(resp.content, "0")
