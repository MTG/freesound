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
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from accounts.models import OldUsername
from geotags.models import GeoTag
from sounds.models import Download, PackDownload, SoundOfTheDay
from utils.search import SearchResultsPaginator
from utils.test_helpers import create_fake_perform_search_engine_query_results_tags_mode, create_user_and_sounds


class SimpleUserTest(TestCase):
    fixtures = ["licenses", "users", "follow"]

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_packs=1, num_sounds=5)
        self.user = user
        self.sound = sounds[0]
        self.sound.original_filename = "a sound name with è+é non-ascii characters"
        self.pack = packs[0]
        self.pack.name = "a pack name with è+é non-ascii characters"
        self.pack.save()
        self.sound.moderation_state = "OK"
        self.sound.processing_state = "OK"
        self.sound.similarity_state = "OK"
        GeoTag.objects.create(sound=self.sound, lat=45.8498, lon=-62.6879, zoom=9)
        self.sound.save()
        SoundOfTheDay.objects.create(sound=self.sound, date_display=datetime.date.today())
        self.download = Download.objects.create(
            user=self.user, sound=self.sound, license=self.sound.license, created=self.sound.created
        )
        self.pack_download = PackDownload.objects.create(user=self.user, pack=self.pack, created=self.pack.created)

    def test_old_ng_redirects(self):
        # Test that some pages which used to have its own "URL" in NG now redirect to other pages and open as a modal

        # Comments on user sounds
        resp = self.client.get(reverse("comments-for-user", kwargs={"username": self.user.username}))
        self.assertRedirects(resp, reverse("account", args=[self.user.username]) + "?comments=1")

        # Comments from a user
        resp = self.client.get(reverse("comments-by-user", kwargs={"username": self.user.username}))
        self.assertRedirects(resp, reverse("account", args=[self.user.username]) + "?comments_by=1")

        # User downloaded sounds
        resp = self.client.get(reverse("user-downloaded-sounds", kwargs={"username": self.user.username}))
        self.assertRedirects(resp, reverse("account", args=[self.user.username]) + "?downloaded_sounds=1")

        # User downloaded packs
        resp = self.client.get(reverse("user-downloaded-packs", kwargs={"username": self.user.username}))
        self.assertRedirects(resp, reverse("account", args=[self.user.username]) + "?downloaded_packs=1")

        # Users that downloaded a sound
        resp = self.client.get(
            reverse("sound-downloaders", kwargs={"username": self.user.username, "sound_id": self.sound.id})
        )
        self.assertRedirects(resp, reverse("sound", args=[self.user.username, self.sound.id]) + "?downloaders=1")

        # Users that downloaded a pack
        resp = self.client.get(
            reverse("pack-downloaders", kwargs={"username": self.user.username, "pack_id": self.pack.id})
        )
        self.assertRedirects(resp, reverse("pack", args=[self.user.username, self.pack.id]) + "?downloaders=1")

        # Users following user
        resp = self.client.get(reverse("user-followers", args=["User2"]))
        self.assertRedirects(resp, reverse("account", args=["User2"]) + "?followers=1")

        # Users followed by user
        resp = self.client.get(reverse("user-following-users", args=["User2"]))
        self.assertRedirects(resp, reverse("account", args=["User2"]) + "?following=1")

        # Tags followed by user
        resp = self.client.get(reverse("user-following-tags", args=["User2"]))
        self.assertRedirects(resp, reverse("account", args=["User2"]) + "?followingTags=1")

        # Sound tags followed by user
        resp = self.client.get(reverse("user-following-tags", args=["User2"]))
        self.assertRedirects(resp, reverse("account", args=["User2"]) + "?followingTags=1")

        # Similar sounds
        resp = self.client.get(reverse("sound-similar", args=[self.user.username, self.sound.id]))
        self.assertRedirects(resp, reverse("sound", args=[self.user.username, self.sound.id]) + "?similar=1")

        # Sound remix group
        resp = self.client.get(reverse("sound-remixes", args=[self.user.username, self.sound.id]))
        self.assertRedirects(resp, reverse("sound", args=[self.user.username, self.sound.id]) + "?remixes=1")

        # Packs for user
        resp = self.client.get(reverse("packs-for-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(reverse("sounds-search") in resp.url and self.user.username in resp.url)

        # Sounds for user
        resp = self.client.get(reverse("sounds-for-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(reverse("sounds-search") in resp.url and self.user.username in resp.url)

        self.client.force_login(self.user)

        # Sound edit page
        resp = self.client.get(reverse("sound-edit-sources", args=[self.user.username, self.sound.id]))
        self.assertRedirects(resp, reverse("sound-edit", args=[self.user.username, self.sound.id]))

        # Flag sound
        resp = self.client.get(reverse("sound-flag", args=[self.user.username, self.sound.id]))
        self.assertRedirects(resp, reverse("sound", args=[self.user.username, self.sound.id]) + "?flag=1")

        # Home to account
        resp = self.client.get(reverse("accounts-home"))
        self.assertRedirects(resp, reverse("account", args=[self.user.username]))

    def test_account_response(self):
        # 200 response on account access
        resp = self.client.get(reverse("account", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_flag_response(self):
        # 200 response on user flag and clear flag access
        self.user.set_password("12345")
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        resp = self.client.get(reverse("flag-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("clear-flags-user", kwargs={"username": self.user.username}), follow=True)
        self.assertContains(resp, f"0 flags cleared for user {self.user.username}")

    def test_user_comments_response(self):
        # 200 response on user comments and comments for user modal
        resp = self.client.get(reverse("comments-for-user", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("comments-by-user", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse("comments-for-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("comments-by-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_geotags_response(self):
        # 200 response on user geotags access
        resp = self.client.get(reverse("geotags-for-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse("geotags-for-user", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_downloaded_response(self):
        # 200 response on user downloaded sounds and packs modals
        resp = self.client.get(reverse("user-downloaded-sounds", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("user-downloaded-packs", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse("user-downloaded-sounds", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("user-downloaded-packs", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_user_follow_response(self):
        # 200 response on user following modals
        resp = self.client.get(reverse("user-following-users", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("user-followers", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("user-following-tags", kwargs={"username": self.user.username}) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)

    def test_download_attribution_csv(self):
        self.client.force_login(self.user)
        # 200 response on download attribution as csv
        resp = self.client.get(reverse("accounts-download-attribution") + "?dl=csv")
        self.assertEqual(resp.status_code, 200)
        # response content as expected
        self.assertContains(
            resp,
            "Download Type,File Name,User,License,Timestamp\r\nP,{0},{1},{0},{6}\r\nS,{2},{3},{4},{5}\r\n".format(
                self.pack.name,
                self.user.username,
                self.sound.original_filename,
                self.user.username,
                self.sound.license,
                self.download.created,
                self.pack_download.created,
            ),
        )

    def test_download_attribution_txt(self):
        self.client.force_login(self.user)
        # 200 response on download attribution as txt
        resp = self.client.get(reverse("accounts-download-attribution") + "?dl=txt")
        self.assertEqual(resp.status_code, 200)
        # response content as expected
        self.assertContains(
            resp,
            "P: {0} by {1} | License: {0} | Timestamp: {6}\nS: {2} by {3} | License: {4} | Timestamp: {5}\n".format(
                self.pack.name,
                self.user.username,
                self.sound.original_filename,
                self.user.username,
                self.sound.license,
                self.download.created,
                self.pack_download.created,
            ),
        )

        # If user is deleted, get 404
        self.user.profile.delete_user()
        resp = self.client.get(reverse("user-following-users", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("user-followers", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("user-following-tags", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 404)

    def test_sounds_response(self):
        # 302 response on sounds page access (since BW, there is a redirect to the search page)
        resp = self.client.get(reverse("sounds"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(reverse("sounds-search") in resp.url)

        # Test other sound related views. Nota that since BW many of these will include redirects
        user = self.sound.user
        user.set_password("12345")
        user.is_superuser = True
        user.save()
        self.client.force_login(user)

        resp = self.client.get(reverse("sound", kwargs={"username": user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse("sound-flag", kwargs={"username": user.username, "sound_id": self.sound.id}) + "?ajax=1"
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(reverse("sound-edit", kwargs={"username": user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(reverse("sound-geotag", kwargs={"username": user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse("sound-similar", kwargs={"username": user.username, "sound_id": self.sound.id}) + "?ajax=1"
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse("sound-downloaders", kwargs={"username": user.username, "sound_id": self.sound.id}) + "?ajax=1"
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse("pack-downloaders", kwargs={"username": user.username, "pack_id": self.pack.id}) + "?ajax=1"
        )
        self.assertEqual(resp.status_code, 200)

    @mock.patch("search.views.perform_search_engine_query")
    def test_tags_response(self, perform_search_engine_query):
        results = create_fake_perform_search_engine_query_results_tags_mode()
        paginator = SearchResultsPaginator(results, 15)
        perform_search_engine_query.return_value = (results, paginator)

        # 200 response on tags page access
        resp = self.client.get(reverse("tags", args=["foley"]), follow=True)
        perform_search_engine_query.assert_called()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["sqp"].tags_mode_active())

    def test_packs_response(self):
        # 302 response (note that since BW, there will be a redirect to the search page in between)
        resp = self.client.get(reverse("packs"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(reverse("sounds-search") in resp.url)

    def test_contact_response(self):
        # 200 response on contact page access
        resp = self.client.get(reverse("contact"))
        self.assertEqual(resp.status_code, 200)

    def test_sound_search_response(self):
        # 200 response on sound search page access
        resp = self.client.get(reverse("sounds-search"))
        self.assertEqual(resp.status_code, 200)

    def test_geotags_embed_response(self):
        # 200 response on geotag box iframe
        resp = self.client.get(reverse("embed-geotags"))
        self.assertEqual(resp.status_code, 200)

    def test_accounts_manage_pages(self):
        # In BW account registration loads as a modal
        resp = self.client.get(reverse("accounts-registration-modal"))
        self.assertEqual(resp.status_code, 200)

        # In BW Account resend activations redirects to "problems logging in" in front page
        resp = self.client.get(reverse("accounts-resend-activation"))
        self.assertEqual(resp.status_code, 302)

        # In BW Account resend activations redirects to "problems logging in" in front page
        resp = self.client.get(reverse("accounts-username-reminder"))
        self.assertEqual(resp.status_code, 302)

        # Login user with moderation permissions
        user = User.objects.create_user("anothertestuser")
        p = Permission.objects.get_by_natural_key("can_moderate", "tickets", "ticket")
        p2 = Permission.objects.get_by_natural_key("can_moderate_forum", "forum", "post")
        user.user_permissions.add(p, p2)
        self.client.force_login(user)

        # 200 response on TOS acceptance page
        resp = self.client.get(reverse("tos-acceptance"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account email reset page
        resp = self.client.get(reverse("accounts-email-reset"))
        self.assertEqual(resp.status_code, 200)

        # In BW, home page does not really exist
        resp = self.client.get(reverse("accounts-home"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("account", args=[user.username]))

        # 200 response on Account edit page
        resp = self.client.get(reverse("accounts-edit"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account edit email settings page
        resp = self.client.get(reverse("accounts-email-settings"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account attribution page
        resp = self.client.get(reverse("accounts-attribution"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account stream page
        resp = self.client.get(reverse("stream"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account messages page
        resp = self.client.get(reverse("messages"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account archived messages page
        resp = self.client.get(reverse("messages-archived"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account sent messages page
        resp = self.client.get(reverse("messages-sent"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account new message page
        resp = self.client.get(reverse("messages-new"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account permissions granted page
        resp = self.client.get(reverse("access-tokens"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on ticket moderation page
        resp = self.client.get(reverse("tickets-moderation-home"))
        self.assertEqual(resp.status_code, 200)

        # 200 response on wiki page
        resp = self.client.get(reverse("wiki"))
        self.assertEqual(resp.status_code, 302)

        # 200 response on forums moderation page
        resp = self.client.get(reverse("forums-moderate"))
        self.assertEqual(resp.status_code, 200)

    def test_username_check(self):
        username = "test_user_new"
        resp = self.client.get(reverse("check_username"), {"username": username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], True)

        user = User.objects.create_user(username, password="testpass")
        resp = self.client.get(reverse("check_username"), {"username": username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        # Now we change the username and we check that both old and new usernames are not valid
        user.username = "other_username"
        user.save()

        # First we check that the OldUsername object is created
        self.assertEqual(OldUsername.objects.filter(username=username, user=user).count(), 1)

        # Now check that check_username will return false for both old and new usernames
        resp = self.client.get(reverse("check_username"), {"username": username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        resp = self.client.get(reverse("check_username"), {"username": user.username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        # Now delete user and check that the username before deleting is still not available because we also
        # forbid reuse of usernames in DeletedUser objects
        user.profile.delete_user()
        resp = self.client.get(reverse("check_username"), {"username": user.username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        # Check that a username that doesn't fit the registration guidelines returns "False", even
        # if the username doesn't exist
        resp = self.client.get(reverse("check_username"), {"username": "username@withat"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        resp = self.client.get(reverse("check_username"), {"username": "username^withcaret"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], False)

        resp = self.client.get(reverse("check_username"), {"username": "username_withunderscore"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result"], True)

    def test_accounts_manage_sounds_pages(self):
        self.client.force_login(self.user)

        # 200 response on manage sounds page - published
        resp = self.client.get(reverse("accounts-manage-sounds", args=["published"]))
        self.assertEqual(resp.status_code, 200)

        # 200 response on manage sounds page - processing
        resp = self.client.get(reverse("accounts-manage-sounds", args=["processing"]))
        self.assertEqual(resp.status_code, 200)

        # 200 response on manage sounds page - pending description
        resp = self.client.get(reverse("accounts-manage-sounds", args=["pending_description"]))
        self.assertEqual(resp.status_code, 200)

        # 200 response on manage sounds page - pending moderation
        resp = self.client.get(reverse("accounts-manage-sounds", args=["pending_moderation"]))
        self.assertEqual(resp.status_code, 200)

        # 200 response on manage sounds page - packs
        resp = self.client.get(reverse("accounts-manage-sounds", args=["packs"]))
        self.assertEqual(resp.status_code, 200)

        # 200 response on manage sounds page - unknown tab
        resp = self.client.get(reverse("accounts-manage-sounds", args=["unknown"]))
        self.assertEqual(resp.status_code, 404)


class OldUserLinksRedirect(TestCase):
    fixtures = ["users"]

    def setUp(self):
        self.user = User.objects.all()[0]

    def test_old_user_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        resp = self.client.get(reverse("old-account-page"), data={"id": self.user.id})
        self.assertEqual(resp.status_code, 301)

    def test_old_user_link_redirect_not_exists_id(self):
        # 404 id does not exist (user with id 999 does not exist in fixture)
        resp = self.client.get(reverse("old-account-page"), data={"id": 999}, follow=True)
        self.assertEqual(resp.status_code, 404)

    def test_old_user_link_redirect_invalid_id(self):
        # 404 invalid id
        resp = self.client.get(reverse("old-account-page"), data={"id": "invalid_id"}, follow=True)
        self.assertEqual(resp.status_code, 404)
