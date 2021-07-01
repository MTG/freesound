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

import datetime

import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from freezegun import freeze_time

import accounts
from accounts.models import EmailPreferenceType
from sounds.models import Sound, SoundOfTheDay, Flag
from sounds.views import get_sound_of_the_day_id
from utils.test_helpers import create_user_and_sounds


class RandomSoundAndUploaderTestCase(TestCase):

    fixtures = ['licenses', 'sounds']

    def test_random_sound(self):
        sound_obj = Sound.objects.random()
        self.assertEqual(isinstance(sound_obj, Sound), True)


class RandomSoundViewTestCase(TestCase):

    fixtures = ['licenses']

    @mock.patch('sounds.views.get_random_sound_from_search_engine')
    def test_random_sound_view(self, random_sound):
        """ Get a sound from solr and redirect to it. """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]

        # We only use the ID field from solr
        random_sound.return_value = {'id': sound.id}

        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))

    @mock.patch('sounds.views.get_random_sound_from_search_engine')
    def test_random_sound_view_bad_solr(self, random_sound):
        """ Solr may send us a sound id which no longer exists (index hasn't been updated).
        In this case, use the database access """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        # Update sound attributes to be selected by Sound.objects.random
        sound.moderation_state = sound.processing_state = 'OK'
        sound.is_explicit = False
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        # We only use the ID field from solr
        random_sound.return_value = {'id': sound.id+100}

        # Even though solr returns sound.id+100, we find we are redirected to the db sound, because
        # we call Sound.objects.random
        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))

    @mock.patch('sounds.views.get_random_sound_from_search_engine')
    def test_random_sound_view_no_solr(self, random_sound):
        """ If solr is down, get a random sound from the database and redirect to it. """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        # Update sound attributes to be selected by Sound.objects.random
        sound.moderation_state = sound.processing_state = 'OK'
        sound.is_explicit = False
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        # Returned if there is an issue accessing solr
        random_sound.return_value = {}

        # we find the sound due to Sound.objects.random
        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))


class RandomSoundTestCase(TestCase):
    """ Test that sounds that don't fall under our criteria don't get selected
        as a random sound."""

    fixtures = ['licenses']

    def _create_test_sound(self):
        """Create a sound which is suitable for being chosen as a random sound"""
        try:
            user = User.objects.get(username="testuser")
        except User.DoesNotExist:
            user = None
        user, packs, sounds = create_user_and_sounds(num_sounds=1, user=user)
        sound = sounds[0]
        sound.is_explicit = False
        sound.moderation_state = 'OK'
        sound.processing_state = 'OK'
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        return sound

    def test_random_sound(self):
        """Correctly selects a random sound"""
        sound = self._create_test_sound()

        random = Sound.objects.random()
        self.assertEqual(random, sound)

    def test_explict(self):
        """Doesn't select a sound if it is marked as explicit"""
        sound = self._create_test_sound()
        sound.is_explicit = True
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_not_processed(self):
        """Doesn't select a sound if it isn't processed"""
        sound = self._create_test_sound()
        sound.processing_state = 'PE'
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

        # or isn't moderated
        sound = self._create_test_sound()
        sound.moderation_state = 'PE'
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_ratings(self):
        """Doesn't select a sound if it doesn't have a high enough rating"""
        sound = self._create_test_sound()
        sound.avg_rating = 4
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_flag(self):
        """Doesn't select a sound if it's flagged"""
        sound = self._create_test_sound()
        sound.save()
        Flag.objects.create(sound=sound, reporting_user=User.objects.all()[0], email="testemail@freesound.org",
            reason_type="O", reason="Not a good sound")

        random = Sound.objects.random()
        self.assertIsNone(random)


class SoundOfTheDayTestCase(TestCase):

    fixtures = ['licenses', 'sounds', 'email_preference_type']

    def setUp(self):
        cache.clear()

    def test_no_random_sound(self):
        # If we have no sound, return None
        random_sound_id = get_sound_of_the_day_id()
        self.assertIsNone(random_sound_id)
        # TODO: If we have some SoundOfTheDay objects, but not for day, don't return them

    def test_random_sound(self):
        sound = Sound.objects.get(id=19)
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date.today())
        random_sound = get_sound_of_the_day_id()
        self.assertEqual(isinstance(random_sound, int), True)

    @freeze_time("2017-06-20")
    def test_create_enough_new_sounds(self):
        """ If we have some random sounds selected for the future, make sure
        that we always have at least settings.NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE sounds
        waiting in the future."""

        sound_ids = []
        user, packs, sounds = create_user_and_sounds(num_sounds=10)
        for s in sounds:
            sound_ids.append(s.id)

        sound = Sound.objects.get(id=19)
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 21))

        call_command("create_random_sounds")

        sound_of_days = SoundOfTheDay.objects.count()
        self.assertEqual(sound_of_days, 6)

    def test_create_sounds_command_clears_random_sound_cache(self):
        """When generating new random sounds with the management command, we should clear
        the cache storing the current random sound to make sure when the sound is needed again
        the correct sound ID will be retrieved from the sound of the day table."""
        cache.set(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY, 1234)
        call_command("create_random_sounds")
        self.assertIsNone(cache.get(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY, None))

    def test_send_email_once(self):
        """If we have a SoundOfTheDay, send the sound's user an email, but only once"""
        sound = Sound.objects.get(id=19)
        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sotd.notify_by_email()

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_RANDOM_SOUND_OF_THE_SAY_CHOOSEN in mail.outbox[0].subject)

        # If we notify again, we don't send another email
        sotd.notify_by_email()
        self.assertEqual(len(mail.outbox), 1)

    def test_user_disable_email_notifications(self):
        """If the chosen Sound's user has disabled email notifications, don't send an email"""
        sound = Sound.objects.get(id=19)

        # Create email preference object for the email type (which will mean user does not want random sound of the
        # day emails as it is enabled by default and the preference indicates user does not want it).
        email_pref = accounts.models.EmailPreferenceType.objects.get(name="random_sound")
        accounts.models.UserEmailSetting.objects.create(user=sound.user, email_type=email_pref)

        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sotd.notify_by_email()

        self.assertEqual(len(mail.outbox), 0)

    @freeze_time("2017-06-20 10:30:00")
    @mock.patch('django.core.cache.cache.set')
    def test_expire_cache_at_end_of_day(self, cache_set):
        """When we cache today's random sound, expire the cache at midnight today"""

        sound = Sound.objects.get(id=19)
        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sound_id = get_sound_of_the_day_id()
        cache_set.assert_called_with(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY, 19, 48600)
