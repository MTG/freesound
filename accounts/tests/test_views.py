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

import datetime

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import OldUsername
from sounds.models import SoundOfTheDay, Download, PackDownload
from utils.test_helpers import create_user_and_sounds


class SimpleUserTest(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_packs=1)
        self.user = user
        self.sound = sounds[0]
        self.sound.original_filename = "a sound name with è+é non-ascii characters"
        self.pack = packs[0]
        self.pack.name = "a pack name with è+é non-ascii characters"
        self.pack.save()
        self.sound.moderation_state = "OK"
        self.sound.processing_state = "OK"
        self.sound.similarity_state = "OK"
        self.sound.save()
        SoundOfTheDay.objects.create(sound=self.sound, date_display=datetime.date.today())
        Download.objects.create(user=self.user, sound=self.sound, license=self.sound.license,
                                created=self.sound.created)
        PackDownload.objects.create(user=self.user, pack=self.pack, created=self.pack.created)

    def test_account_response(self):
        # 200 response on account access
        resp = self.client.get(reverse('account', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_sounds_response(self):
        # 200 response on user sounds access
        resp = self.client.get(reverse('sounds-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_flag_response(self):
        # 200 response on user flag and clear flag access
        self.user.set_password('12345')
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        resp = self.client.get(reverse('flag-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('clear-flags-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_comments_response(self):
        # 200 response on user comments and comments for user access
        resp = self.client.get(reverse('comments-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('comments-by-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse('comments-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('comments-by-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_geotags_response(self):
        # 200 response on user geotags access
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_packs_response(self):
        # 200 response on user packs access
        resp = self.client.get(reverse('packs-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_downloaded_response(self):
        # 200 response on user downloaded sounds and packs access
        resp = self.client.get(reverse('user-downloaded-sounds', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-downloaded-packs', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse('user-downloaded-sounds', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('user-downloaded-packs', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_follow_response(self):
        # 200 response on user user bookmarks sounds and packs access
        resp = self.client.get(reverse('user-following-users', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-followers', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-following-tags', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_download_attribution_csv(self):
        self.client.force_login(self.user)
        # 200 response on download attribution as csv
        resp = self.client.get(reverse('accounts-download-attribution') + '?dl=csv')
        self.assertEqual(resp.status_code, 200)
        # response content as expected
        self.assertEqual(resp.content,
                         'Download Type,File Name,User,License\r\nP,{0},{1},{0}\r\nS,{2},{3},{4}\r\n'.format(
                             self.pack.name, self.user.username, self.sound.original_filename, self.user.username,
                             self.sound.license))

    def test_download_attribution_txt(self):
        self.client.force_login(self.user)
        # 200 response on download attribution as txt
        resp = self.client.get(reverse('accounts-download-attribution') + '?dl=txt')
        self.assertEqual(resp.status_code, 200)
        # response content as expected
        self.assertEqual(resp.content,
                         'P: {0} by {1} | License: {0}\nS: {2} by {3} | License: {4}\n'.format(
                             self.pack.name, self.user.username, self.sound.original_filename, self.user.username,
                             self.sound.license))


        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse('user-following-users', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('user-followers', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('user-following-tags', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_sounds_response(self):
        # 200 response on sounds page access
        resp = self.client.get(reverse('sounds'))
        self.assertEqual(resp.status_code, 200)

        user = self.sound.user
        user.set_password('12345')
        user.is_superuser = True
        user.save()
        self.client.force_login(user)
        resp = self.client.get(reverse('sound', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-flag', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(
            reverse('sound-edit-sources', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-edit', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-geotag', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-similar', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-delete', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(
            reverse('sound-downloaders', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)

    def test_tags_response(self):
        # 200 response on tags page access
        resp = self.client.get(reverse('tags'))
        self.assertEqual(resp.status_code, 200)

    def test_packs_response(self):
        # 200 response on packs page access
        resp = self.client.get(reverse('packs'))
        self.assertEqual(resp.status_code, 200)

    def test_comments_response(self):
        # 200 response on comments page access
        resp = self.client.get(reverse('comments'))
        self.assertEqual(resp.status_code, 200)

    def test_remixed_response(self):
        # 200 response on remixed sounds page access
        resp = self.client.get(reverse('remix-groups'))
        self.assertEqual(resp.status_code, 200)

    def test_contact_response(self):
        # 200 response on contact page access
        resp = self.client.get(reverse('contact'))
        self.assertEqual(resp.status_code, 200)

    def test_sound_search_response(self):
        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'))
        self.assertEqual(resp.status_code, 200)

    def test_geotags_box_response(self):
        # 200 response on geotag box page access
        resp = self.client.get(reverse('geotags-box'))
        self.assertEqual(resp.status_code, 200)

    def test_geotags_box_iframe_response(self):
        # 200 response on geotag box iframe
        resp = self.client.get(reverse('embed-geotags-box-iframe'))
        self.assertEqual(resp.status_code, 200)

    def test_accounts_manage_pages(self):
        # 200 response on Account registration page
        resp = self.client.get(reverse('accounts-register'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account reactivation page
        resp = self.client.get(reverse('accounts-resend-activation'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account username reminder page
        resp = self.client.get(reverse('accounts-username-reminder'))
        self.assertEqual(resp.status_code, 200)

        # Login user with moderation permissions
        user = User.objects.create_user("anothertestuser")
        p = Permission.objects.get_by_natural_key('can_moderate', 'tickets', 'ticket')
        p2 = Permission.objects.get_by_natural_key('can_moderate_forum', 'forum', 'post')
        user.user_permissions.add(p, p2)
        self.client.force_login(user)

        # 200 response on TOS acceptance page
        resp = self.client.get(reverse('tos-acceptance'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account email reset page
        resp = self.client.get(reverse('accounts-email-reset'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account home page
        resp = self.client.get(reverse('accounts-home'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account edit page
        resp = self.client.get(reverse('accounts-edit'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account edit email settings page
        resp = self.client.get(reverse('accounts-email-settings'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account attribution page
        resp = self.client.get(reverse('accounts-attribution'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account stream page
        resp = self.client.get(reverse('stream'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account messages page
        resp = self.client.get(reverse('messages'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account archived messages page
        resp = self.client.get(reverse('messages-archived'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account sent messages page
        resp = self.client.get(reverse('messages-sent'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account new message page
        resp = self.client.get(reverse('messages-new'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account permissions granted page
        resp = self.client.get(reverse('access-tokens'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on ticket moderation page
        resp = self.client.get(reverse('tickets-moderation-home'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on wiki page
        resp = self.client.get(reverse('wiki'))
        self.assertEqual(resp.status_code, 302)

        # 200 response on forums moderation page
        resp = self.client.get(reverse('forums-moderate'))
        self.assertEqual(resp.status_code, 200)

    def test_username_check(self):
        username = 'test_user_new'
        resp = self.client.get(reverse('check_username'),
                               {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], True)

        user = User.objects.create_user(username, password="testpass")
        resp = self.client.get(reverse('check_username'),
                               {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        # Now we change the username and we check that both old and new usernames are not valid
        user.username = 'other_username'
        user.save()

        # First we check that the OldUsername object is created
        self.assertEqual(OldUsername.objects.filter(username=username, user=user).count(), 1)

        # Now check that check_username will return false for both old and new usernames
        resp = self.client.get(reverse('check_username'),
                               {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        resp = self.client.get(reverse('check_username'),
                               {'username': user.username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        # Now delete user and check that the username before deleting is still not available because we also
        # forbid reuse of usernames in DeletedUser objects
        user.profile.delete_user()
        resp = self.client.get(reverse('check_username'),
                               {'username': user.username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        # Check that a username that doesn't fit the registration guidelines returns "False", even
        # if the username doesn't exist
        resp = self.client.get(reverse('check_username'),
                               {'username': 'username@withat'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        resp = self.client.get(reverse('check_username'),
                               {'username': 'username^withcaret'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        resp = self.client.get(reverse('check_username'),
                               {'username': 'username_withunderscore'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], True)


class OldUserLinksRedirect(TestCase):
    fixtures = ['users']

    def setUp(self):
        self.user = User.objects.all()[0]

    def test_old_user_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        resp = self.client.get(reverse('old-account-page'), data={'id': self.user.id})
        self.assertEqual(resp.status_code, 301)

    def test_old_user_link_redirect_not_exists_id(self):
        # 404 id does not exist (user with id 999 does not exist in fixture)
        resp = self.client.get(reverse('old-account-page'), data={'id': 999}, follow=True)
        self.assertEqual(resp.status_code, 404)

    def test_old_user_link_redirect_invalid_id(self):
        # 404 invalid id
        resp = self.client.get(reverse('old-account-page'), data={'id': 'invalid_id'}, follow=True)
        self.assertEqual(resp.status_code, 404)
