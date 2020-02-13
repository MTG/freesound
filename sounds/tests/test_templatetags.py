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

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse

from sounds.models import Sound


class DisplaySoundTemplatetagTestCase(TestCase):

    fixtures = ['licenses', 'sounds_with_tags']

    def setUp(self):
        # A sound which has tags
        self.sound = Sound.objects.get(pk=23)

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_id(self):
        """Test that when using the display_sound templatetag with a sound ID as parameter we make only one DB query
        and all needed metadata for rendering the template is loaded properly.
        """
        request = HttpRequest()
        request.user = AnonymousUser()
        with self.assertNumQueries(1):
            Template("{% load display_sound %}{% display_sound sound %}").render(Context({
                'sound': self.sound.id,
                'request': request,
                'media_url': 'http://example.org/'
            }))
            #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_standard_sound_obj(self):
        """Test that when using the display_sound templatetag with a standard Sound object parameter we make only one
        DB query (to get extra needed metadata) and all needed metadata for rendering the template is loaded properly.
        """
        request = HttpRequest()
        request.user = AnonymousUser()
        with self.assertNumQueries(1):
            Template("{% load display_sound %}{% display_sound sound %}").render(Context({
                'sound': self.sound,
                'request': request,
                'media_url': 'http://example.org/'
            }))
            #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_bulk_query_id_sound_obj(self):
        """Test that when using the display_sound templatetag with a Sound object parameter retrieved using
        Sound.objects.bulk_query_id we make no extra DB queries and all needed metadata for rendering the template is
        loaded properly.
        """
        self.sound = Sound.objects.bulk_query_id([23])[0]
        request = HttpRequest()
        request.user = AnonymousUser()
        with self.assertNumQueries(0):
            Template("{% load display_sound %}{% display_sound sound %}").render(Context({
                'sound': self.sound,
                'request': request,
                'media_url': 'http://example.org/'
            }))
            #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_bad_id(self):
        """Test that when using display_sound templatetag with an invalid sound ID as a parameter we make no extra
        DB queries and no exceptions are raised.
        """
        request = HttpRequest()
        request.user = AnonymousUser()
        with self.assertNumQueries(0):
            Template("{% load display_sound %}{% display_sound sound %}").render(Context({
                'sound': 'not_an_integer',
                'request': request,
                'media_url': 'http://example.org/'
            }))
            #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_unexisting_sound_id(self):
        """Test that when using display_sound templatetag with an non-existing sound ID as a parameter we make only
        one DB query and no exceptions are raised.
        """
        request = HttpRequest()
        request.user = AnonymousUser()
        with self.assertNumQueries(1):
            Template("{% load display_sound %}{% display_sound sound %}").render(Context({
                'sound': -1,
                'request': request,
                'media_url': 'http://example.org/'
            }))
            #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    def test_display_sound_wrapper_view(self):
        response = self.client.get(reverse('sound-display', args=[self.sound.user.username, 921]))  # Non existent ID
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('sound-display', args=[self.sound.user.username, self.sound.id]))
        self.assertEqual(response.status_code, 200)