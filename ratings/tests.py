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
from django.contrib.auth.models import User
from django.db.models import Max
from django.test import override_settings
from pytest_django.asserts import assertContains, assertNotContains

import ratings.models
import sounds.models
from utils.test_helpers import create_user_and_sounds


@pytest.fixture
def rating_licenses(load_fixtures):
    load_fixtures(["licenses"])


@pytest.fixture
def rating_sound(rating_licenses, load_fixtures):
    load_fixtures(["sounds"])
    return sounds.models.Sound.objects.get(pk=16)


@pytest.fixture
def rating_user(db):
    return User.objects.create_user("testuser1", email="testuser1@freesound.org", password="testpass")


@pytest.fixture
def rating_users(rating_user):
    user2 = User.objects.create_user("testuser2", email="testuser2@freesound.org", password="testpass")
    user3 = User.objects.create_user("testuser3", email="testuser3@freesound.org", password="testpass")
    return rating_user, user2, user3


@pytest.fixture
def rating_page_data(rating_sound, rating_user, load_fixtures):
    load_fixtures(["user_groups"])
    return rating_sound, rating_user


class TestRatings:
    def test_rating_normal(self, rating_sound, rating_users, client):
        """Add a rating"""
        sound = rating_sound
        user1, user2, _ = rating_users
        assert sound.num_ratings == 0
        client.force_login(user1)

        # One rating from a different user
        r = ratings.models.SoundRating.objects.create(sound_id=sound.id, user_id=user2.id, rating=2)

        # Test signal updated sound.avg_rating
        sound.refresh_from_db()
        assert sound.avg_rating == 2.0
        assert sound.num_ratings == 1

        RATING_VALUE = 3
        resp = client.get(f"/people/Anton/sounds/{sound.id}/rate/{RATING_VALUE}/")
        assert resp.status_code == 200
        assert resp.json()["num_ratings"] == 2

        assert ratings.models.SoundRating.objects.count() == 2
        r = ratings.models.SoundRating.objects.get(sound_id=sound.id, user_id=user1.id)
        # Ratings in the database are 2x the value from the web call
        assert r.rating == 2 * RATING_VALUE

        # Check that signal updated sound.avg_rating and sound.num_ratings
        sound.refresh_from_db()
        assert sound.avg_rating == 4.0
        assert sound.num_ratings == 2

        # Delete one rating and check if signal updated avg_rating and num_ratings
        r.delete()
        sound.refresh_from_db()
        assert sound.avg_rating == 2.0
        assert sound.num_ratings == 1

    def test_rating_change(self, rating_sound, rating_users, client):
        """Change your existing rating."""
        sound = rating_sound
        user1, _, _ = rating_users
        client.force_login(user1)

        r = ratings.models.SoundRating.objects.create(sound_id=sound.id, user_id=user1.id, rating=4)

        resp = client.get(f"/people/Anton/sounds/{sound.id}/rate/{5}/")
        assert resp.status_code == 200
        assert resp.json()["num_ratings"] == 1
        assert resp.json()["avg_rating"] == 10.0
        newr = ratings.models.SoundRating.objects.first()
        assert ratings.models.SoundRating.objects.count() == 1
        # Ratings in the database are 2x the value from the web call
        assert newr.rating == 10

        # Check that signal updated sound.avg_rating. Number of ratings is still the same
        sound.refresh_from_db()
        assert sound.avg_rating == 10.0
        assert sound.num_ratings == 1

    def test_rating_out_of_range(self, rating_sound, rating_users, client):
        """Change rating by a value which is not 1-5."""
        sound = rating_sound
        user1, _, _ = rating_users
        client.force_login(user1)

        # Check both boundaries; neither request should store a rating.
        for rating in (0, 6):
            resp = client.get(f"/people/Anton/sounds/{sound.id}/rate/{rating}/")
            assert resp.status_code == 200
            assert resp.json()["num_ratings"] == 0
            assert resp.json()["avg_rating"] == 0
            assert not ratings.models.SoundRating.objects.filter(sound=sound).exists()
            sound.refresh_from_db()
            assert sound.num_ratings == 0
            assert sound.avg_rating == 0

    def test_delete_all_ratings(self, rating_sound, rating_users):
        sound = rating_sound
        _, user2, _ = rating_users
        r = ratings.models.SoundRating.objects.create(sound=sound, user_id=user2.id, rating=2)
        sound.refresh_from_db()
        assert sound.num_ratings == 1
        r.delete()
        sound.refresh_from_db()
        assert sound.num_ratings == 0

    def test_rating_no_sound(self, rating_sound, rating_users, client):
        """Test behaviour if the sound id doesn't exist"""
        sound = rating_sound
        user1, _, _ = rating_users
        max_id = sounds.models.Sound.objects.all().aggregate(Max("id"))
        max_id = max_id["id__max"]
        no_id = max_id + 20

        client.force_login(user1)

        resp = client.get(f"/people/Anton/sounds/{no_id}/rate/{2}/")
        assert resp.status_code == 404

        # If sound id doesn't match username
        resp = client.get(f"/people/NotAnton/sounds/{sound.id}/rate/{2}/")
        assert resp.status_code == 404

    @override_settings(MIN_NUMBER_RATINGS=3)
    def test_avg_rating_pack_model(self, rating_licenses, rating_users):
        user1, user2, user3 = rating_users
        _, packs, sound = create_user_and_sounds(num_sounds=3, num_packs=1)
        pack = packs[0]

        # Check that the average rating is 0 when there are no ratings for the sounds in the pack
        assert pack.avg_rating == 0

        # Rate some sounds, but avg rating is still 0 because none of the sounds has been rated at least MIN_NUMBER_RATINGS number of times
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[0], rating=4)
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[1], rating=6)
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[2], rating=5)
        assert pack.avg_rating == 0

        # Now rate sounds again until MIN_NUMBER_RATINGS is reached per sound
        ratings.models.SoundRating.objects.create(user=user2, sound=sound[0], rating=4)
        ratings.models.SoundRating.objects.create(user=user2, sound=sound[1], rating=6)
        ratings.models.SoundRating.objects.create(user=user2, sound=sound[2], rating=5)
        ratings.models.SoundRating.objects.create(user=user3, sound=sound[0], rating=4)
        ratings.models.SoundRating.objects.create(user=user3, sound=sound[1], rating=6)
        ratings.models.SoundRating.objects.create(user=user3, sound=sound[2], rating=5)

        # Finally pack avg rating should be the avg of the avg_rating of each individual sound
        assert pack.avg_rating == 5

    def test_avg_rating_profile_model(self, rating_licenses, rating_users):
        user1, user2, _ = rating_users
        user, _, sound = create_user_and_sounds(num_sounds=3)

        # Check that the average rating is 0 when there are no ratings for the sounds of the user
        assert user.profile.avg_rating == 0

        # Rate some sounds and check that avg_rating is updated accordingly. There is no MIN_NUMBER_RATINGS for user avg_rating
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[0], rating=4)
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[1], rating=6)
        ratings.models.SoundRating.objects.create(user=user1, sound=sound[2], rating=5)
        assert user.profile.avg_rating == 5

        # Check that avg rating is updated when sounds get more ratings
        ratings.models.SoundRating.objects.create(user=user2, sound=sound[0], rating=2)  # sound will have avg_rating 3
        ratings.models.SoundRating.objects.create(user=user2, sound=sound[1], rating=8)  # sound will have avg_rating 7
        ratings.models.SoundRating.objects.create(
            user=user2, sound=sound[2], rating=10
        )  # sound will have avg_rating 7.5

        # Finally user avg rating should be the avg of the avg_rating of each individual sound
        assert round(user.profile.avg_rating, 2) == 5.83


class TestRatingsPage:
    def test_rating_link_logged_in(self, rating_page_data, client):
        """A logged in user viewing a sound should get links to rate the sound"""
        sound, user = rating_page_data
        client.force_login(user)
        resp = client.get(sound.get_absolute_url())
        assertContains(resp, f'<label for="rate-{sound.id}-1" data-value="1" aria-label="Rate sound 1 star">')

    def test_no_rating_link_logged_out(self, rating_page_data, client):
        """A logged out user doesn't see links to rate a sound"""
        sound, _ = rating_page_data
        resp = client.get(sound.get_absolute_url())
        assertNotContains(resp, f'<label for="rate-{sound.id}-1" data-value="1" aria-label="Rate sound 1 star">')

    def test_no_rating_link_own_sound(self, rating_page_data, client):
        """A user doesn't see links to rate their own sound"""
        sound, _ = rating_page_data
        user = User.objects.get(username="Anton")
        client.force_login(user)
        resp = client.get(sound.get_absolute_url())
        assertNotContains(resp, f'<label for="rate-{sound.id}-1" data-value="1" aria-label="Rate sound 1 star">')
