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

import os
from unittest import mock, skipIf

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from sounds.forms import PackForm
from sounds.models import BulkUploadProgress, License, Pack, Sound
from tags.models import Tag
from utils.test_helpers import (
    create_test_files,
    create_user_and_sounds,
    override_csv_path_with_temp_directory,
    override_uploads_path_with_temp_directory,
)


class UserUploadAndDescribeSounds(TestCase):
    fixtures = ["licenses", "user_groups", "email_preference_type"]

    @skipIf(True, "Test not ready for new uploader")
    @override_uploads_path_with_temp_directory
    def test_handle_uploaded_file_html(self):
        # TODO: test html5 file uploads when we change uploader
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)

        # Test successful file upload
        filename = "file.wav"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post("/home/upload/html/", {"file": f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(os.path.join(settings.UPLOADS_PATH, str(user.id), filename)), True)

        # Test file upload that should fail
        filename = "filè.xyz"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post("/home/upload/html/", {"file": f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(os.path.join(settings.UPLOADS_PATH, str(user.id), filename)), False)

    @override_uploads_path_with_temp_directory
    def test_select_uploaded_files_to_describe(self):
        # Create audio files
        filenames = ["file1.wav", "file2.wav", "file3.wav", "filè4.wav"]
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)
        user_upload_path = os.path.join(settings.UPLOADS_PATH, str(user.id))
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)

        # Check that files are displayed in the template
        resp = self.client.get(reverse("accounts-manage-sounds", args=["pending_description"]))
        self.assertEqual(resp.status_code, 200)
        self.assertListEqual(
            sorted([os.path.basename(f.full_path) for f in resp.context["file_structure"].children]), sorted(filenames)
        )

        # Selecting one file redirects to /home/describe/sounds/
        sounds_to_describe_idx = [0]
        resp = self.client.post(
            reverse("accounts-manage-sounds", args=["pending_description"]),
            {
                "describe": "describe",
                "sound-files": [
                    f"file{idx}" for idx in sounds_to_describe_idx
                ],  # Note this is not the filename but the value of the "select" option
            },
        )
        session_key_prefix = resp.url.split("session=")[1]
        self.assertRedirects(resp, reverse("accounts-describe-sounds") + f"?session={session_key_prefix}")
        self.assertEqual(
            self.client.session[f"{session_key_prefix}-len_original_describe_sounds"], len(sounds_to_describe_idx)
        )
        self.assertListEqual(
            sorted(
                [os.path.basename(f["full_path"]) for f in self.client.session[f"{session_key_prefix}-describe_sounds"]]
            ),
            sorted([filenames[idx] for idx in sounds_to_describe_idx]),
        )

        # Selecting multiple file redirects to /home/describe/license/
        sounds_to_describe_idx = [1, 2, 3]
        resp = self.client.post(
            reverse("accounts-manage-sounds", args=["pending_description"]),
            {
                "describe": "describe",
                "sound-files": [
                    f"file{idx}" for idx in sounds_to_describe_idx
                ],  # Note this is not the filename but the value of the "select" option
            },
        )
        session_key_prefix = resp.url.split("session=")[1]
        self.assertRedirects(resp, reverse("accounts-describe-license") + f"?session={session_key_prefix}")
        self.assertEqual(
            self.client.session[f"{session_key_prefix}-len_original_describe_sounds"], len(sounds_to_describe_idx)
        )
        self.assertListEqual(
            sorted(
                [os.path.basename(f["full_path"]) for f in self.client.session[f"{session_key_prefix}-describe_sounds"]]
            ),
            sorted([filenames[idx] for idx in sounds_to_describe_idx]),
        )

        # Selecting files to delete, deletes the files
        sounds_to_delete_idx = [1, 2, 3]
        resp = self.client.post(
            reverse("accounts-manage-sounds", args=["pending_description"]),
            {
                "delete_confirm": "delete_confirm",
                "sound-files": [
                    f"file{idx}" for idx in sounds_to_delete_idx
                ],  # Note this is not the filename but the value of the "select" option,
            },
        )
        self.assertRedirects(resp, reverse("accounts-manage-sounds", args=["pending_description"]))
        self.assertEqual(len(os.listdir(user_upload_path)), len(filenames) - len(sounds_to_delete_idx))

    @override_uploads_path_with_temp_directory
    def test_describe_selected_files(self):
        # Create audio files
        filenames = ["file1.wav", "filè2.wav"]
        user = User.objects.create_user("testuser", email="1@xmpl.com", password="testpass")
        self.client.force_login(user)
        user_upload_path = os.path.join(settings.UPLOADS_PATH, str(user.id))
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)
        _, _, sound_sources = create_user_and_sounds(
            num_sounds=3,
            num_packs=0,
            user=User.objects.create_user("testuser2", email="2@xmpl.com", password="testpass"),
        )  # These sounds will be used as sources for an uploaded sound

        # Set license and pack data in session
        session = self.client.session
        session_key_prefix = "304298eb"
        session[f"{session_key_prefix}-describe_license"] = License.objects.all()[0].id
        session[f"{session_key_prefix}-describe_pack"] = False
        session[f"{session_key_prefix}-len_original_describe_sounds"] = 2
        session[f"{session_key_prefix}-describe_sounds"] = [
            {"name": filenames[0], "full_path": os.path.join(user_upload_path, filenames[0])},
            {"name": filenames[1], "full_path": os.path.join(user_upload_path, filenames[1])},
        ]
        session.save()

        # Post description information
        resp = self.client.post(
            f"/home/describe/sounds/?session={session_key_prefix}",
            {
                "0-audio_filename": filenames[0],
                "0-lat": "46.31658418182218",
                "0-lon": "3.515625",
                "0-zoom": "16",
                "0-tags": "testtag1 testtag2 testtag3",
                "0-pack": PackForm.NO_PACK_CHOICE_VALUE,
                "0-license": "3",
                "0-description": "a test description for the sound file",
                "0-new_pack": "",
                "0-bst_category": "ss-n",
                "0-name": filenames[0],
                "1-audio_filename": filenames[1],
                "1-license": "3",
                "1-description": "another test description",
                "1-lat": "",
                "1-pack": PackForm.NO_PACK_CHOICE_VALUE,
                "1-lon": "",
                "1-bst_category": "fx-o",
                "1-name": filenames[1],
                "1-new_pack": "Name of a new pack",
                "1-zoom": "",
                "1-tags": "testtag1 testtag4 testtag5",
                "1-sources": ",".join([f"{s.id}" for s in sound_sources]),
            },
            follow=True,
        )

        # Check that post redirected to first describe page with confirmation message on sounds described
        self.assertRedirects(resp, "/home/sounds/manage/processing/")
        self.assertEqual(
            "Successfully finished sound description round" in list(resp.context["messages"])[2].message, True
        )

        # Check that sounds have been created along with related tags, geotags and packs
        self.assertEqual(user.sounds.all().count(), 2)
        self.assertListEqual(
            sorted(list(user.sounds.values_list("original_filename", flat=True))), sorted([f for f in filenames])
        )
        self.assertEqual(Pack.objects.filter(name="Name of a new pack").exists(), True)
        self.assertEqual(Tag.objects.filter(name__contains="testtag").count(), 5)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[0]).geotag, None)
        self.assertEqual(user.sounds.get(original_filename=filenames[0]).bst_category, "ss-n")
        sound_with_sources = user.sounds.get(original_filename=filenames[1])
        self.assertEqual(sound_with_sources.sources.all().count(), len(sound_sources))


class BulkDescribe(TestCase):
    fixtures = ["licenses", "user_groups"]

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=40)
    def test_can_do_bulk_describe(self):
        user = User.objects.create_user("testuser")

        # Newly created user can't do bulk upload
        self.assertFalse(user.profile.can_do_bulk_upload())

        # When user has uploaded BULK_UPLOAD_MIN_SOUNDS, now she can bulk upload
        user.profile.num_sounds = settings.BULK_UPLOAD_MIN_SOUNDS
        self.assertTrue(user.profile.can_do_bulk_upload())

        # If user is whitelisted, she can bulk upload
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.can_do_bulk_upload())
        user.profile.is_whitelisted = True
        self.assertTrue(user.profile.can_do_bulk_upload())

        # If user is assigned the bulk_uploaders group then bulk upload is allowed
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.can_do_bulk_upload())
        group = Group.objects.get(name="bulk_uploaders")
        user.groups.add(group)
        # Reload object from db to refresh permission's caches (Note that refresh_from_db() doesn't clear perms cache)
        user = User.objects.get(id=user.id)
        self.assertTrue(user.profile.can_do_bulk_upload())

    @override_csv_path_with_temp_directory
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    @mock.patch("general.tasks.validate_bulk_describe_csv.delay")
    def test_upload_csv(self, submit_job):
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)

        # Test successful file upload and redirect
        filename = "file.csv"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post(reverse("accounts-manage-sounds", args=["pending_description"]), {"bulk-csv_file": f})
        bulk = BulkUploadProgress.objects.get(user=user)
        self.assertRedirects(resp, reverse("accounts-bulk-describe", args=[bulk.id]))

        # Test really file exists
        self.assertEqual(os.path.exists(bulk.csv_path), True)

        # Test job is triggered
        submit_job.assert_called_once_with(bulk_upload_progress_object_id=bulk.id)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_view_permissions(self):
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")

        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        expected_redirect_url = reverse("login") + "?next=%s" % reverse("accounts-bulk-describe", args=[bulk.id])
        self.assertRedirects(resp, expected_redirect_url)  # If user not logged in, redirect to login page

        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertEqual(resp.status_code, 200)  # After login, page loads normally (200 OK)

        user = User.objects.create_user("testuser2", email="another_email@example.com")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertEqual(resp.status_code, 404)  # User without permission (not owner of object) gets 404

        with self.settings(BULK_UPLOAD_MIN_SOUNDS=10):
            # Now user is not allowed to load the page as user.profile.can_do_bulk_upload() returns False
            self.client.force_login(user)
            resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]), follow=True)
            self.assertRedirects(resp, reverse("accounts-manage-sounds", args=["pending_description"]))
            self.assertContains(resp, "Your user does not have permission to use the bulk describe")

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_validating(self):
        # Test that when BulkUploadProgress has not finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "The uploaded data file has not yet been validated")

    @mock.patch("general.tasks.bulk_describe.delay")
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_finished_validation(self, submit_job):
        # Test that when BulkUploadProgress has finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "Validation results of the data file")

        # Test that choosing option to delete existing BulkUploadProgress really does it
        resp = self.client.post(reverse("accounts-bulk-describe", args=[bulk.id]), data={"delete": True})
        self.assertRedirects(
            resp, reverse("accounts-manage-sounds", args=["pending_description"])
        )  # Redirects to describe page after delete
        self.assertEqual(BulkUploadProgress.objects.filter(user=user).count(), 0)

        # Test that choosing option to start describing files triggers bulk describe job
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        resp = self.client.post(reverse("accounts-bulk-describe", args=[bulk.id]), data={"start": True})
        self.assertEqual(resp.status_code, 200)
        submit_job.assert_called_once_with(bulk_upload_progress_object_id=bulk.id)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_description_in_progress(self):
        # Test that when BulkUploadProgress has started description and processing we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="S", user=user, original_csv_filename="test.csv")
        bulk.validation_output = {
            "lines_ok": list(range(1, 10)),
            "lines_with_errors": [],
            "global_errors": [],
        }
        bulk.save()
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "Your sounds are being described and processed")

        # Test that when BulkUploadProgress has finished describing items but still is processing some sounds, we
        # show that info to the users. First we fake some data for the bulk object
        bulk.progress_type = "F"
        bulk.validation_output = {
            "lines_ok": list(
                range(5)
            ),  # NOTE: we only use the length of these lists, so we fill them with irrelevant data
            "lines_with_errors": list(range(2)),
            "global_errors": [],
        }
        bulk.description_output = {
            "1": 1,  # NOTE: we only use the length of the dict so we fill it with irrelevant values/keys
            "2": 2,
            "3": 3,
        }
        bulk.save()
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "Your sounds are being described and processed")

        # Test that when both description and processing have finished we show correct info to users
        for i in range(5):  # First create the sound objects so BulkUploadProgress can properly compute progress
            Sound.objects.create(
                user=user,
                original_filename="Test sound %i" % i,
                license=License.objects.all()[0],
                md5="fakemd5%i" % i,
                moderation_state="OK",
                processing_state="OK",
            )

        bulk.progress_type = "F"
        bulk.description_output = {}
        for count, sound in enumerate(user.sounds.all()):
            bulk.description_output[count] = sound.id  # Fill bulk.description_output with real sound IDs
        bulk.save()
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "The bulk description process has finished!")

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_closed(self):
        # Test that when BulkUploadProgress object is closed we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="C", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts-bulk-describe", args=[bulk.id]))
        self.assertContains(resp, "This bulk description process is closed")


class SessionJsonSafetyTests(TestCase):
    """Regression guard: every value the upload/describe/edit flow writes to request.session
    must be JSON-serialisable, so SESSION_SERIALIZER can be flipped to JSONSerializer in a
    follow-up PR. If this test goes red, something in the flow is putting a Python object
    (Sound/License/Pack/File/...) back into the session."""

    fixtures = ["licenses", "user_groups", "email_preference_type"]

    def _assert_session_json_safe(self):
        from django.contrib.sessions.serializers import JSONSerializer

        serializer = JSONSerializer()
        for key, value in self.client.session.items():
            try:
                serializer.dumps({key: value})
            except TypeError as exc:
                self.fail(f"Session key {key!r} holds a non-JSON-safe value (type={type(value).__name__!r}): {exc}")

    def _assert_session_value(self, prefix, key, expected):
        """The key must be present AND equal to `expected`, so that a producer write which
        is silently skipped (the key never appears) fails loudly instead of letting the
        json-safety sweep above pass over a session that never got the value at all."""
        full_key = f"{prefix}-{key}"
        self.assertIn(full_key, self.client.session, f"producer never wrote {full_key!r}")
        self.assertEqual(self.client.session[full_key], expected)

    @override_uploads_path_with_temp_directory
    def test_describe_flow_session_is_json_safe(self):
        filenames = ["file1.wav", "file2.wav"]
        user = User.objects.create_user("testuser", email="json@xmpl.com", password="testpass")
        self.client.force_login(user)
        user_upload_path = settings.UPLOADS_PATH + "/%i/" % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)

        # Step 1: select files from pending_description -> writes describe_sounds, len_original_describe_sounds.
        # generate_tree() assigns file ids starting at "file0".
        resp = self.client.post(
            reverse("accounts-manage-sounds", args=["pending_description"]),
            {"describe": "describe", "sound-files": ["file0", "file1"]},
        )
        self.assertEqual(resp.status_code, 302)
        session_key_prefix = resp.url.split("session=")[1]
        describe_sounds = self.client.session[f"{session_key_prefix}-describe_sounds"]
        self.assertTrue(
            isinstance(describe_sounds, list)
            and all(isinstance(f, dict) and set(f) == {"name", "full_path"} for f in describe_sounds),
            f"describe_sounds should be a list of name/full_path dicts, got {describe_sounds!r}",
        )
        self._assert_session_value(session_key_prefix, "len_original_describe_sounds", 2)
        self._assert_session_json_safe()

        # Step 2: pick a license -> writes describe_license.
        # Must be a license that is actually valid in LicenseForm's queryset (the
        # describe_license view uses hide_old_license_versions=True). "Attribution" (4.0) is
        # in the queryset and survives the 3.0 clean check, so the producer actually runs --
        # using License.objects.all()[0] would (nondeterministically) pick "Sampling+", which
        # is not a valid choice, the form would be invalid and the write silently skipped.
        attribution = License.objects.get(name="Attribution")
        resp = self.client.post(
            reverse("accounts-describe-license") + f"?session={session_key_prefix}",
            {"license": str(attribution.id)},
        )
        self.assertEqual(resp.status_code, 302)
        self._assert_session_value(session_key_prefix, "describe_license", attribution.id)
        self._assert_session_json_safe()

        # Step 3: pick "no pack" -> writes describe_pack (= False sentinel)
        resp = self.client.post(
            reverse("accounts-describe-pack") + f"?session={session_key_prefix}",
            {"pack-pack": PackForm.NO_PACK_CHOICE_VALUE, "pack-new_pack": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self._assert_session_value(session_key_prefix, "describe_pack", False)
        self._assert_session_json_safe()

    def test_describe_pack_id_branches_are_json_safe(self):
        # describe_pack writes the …-describe_pack key independently of earlier steps, so we
        # exercise each branch against its own fresh session prefix. The two `.id` branches
        # (existing pack, new pack) are the ones that previously stored a Pack instance and
        # are not reached by the "no pack" path in test_describe_flow_session_is_json_safe.
        user = User.objects.create_user("packuser", email="pack@xmpl.com", password="testpass")
        self.client.force_login(user)

        # Existing pack -> stores data["pack"].id
        existing_pack = Pack.objects.create(user=user, name="Existing pack")
        resp = self.client.post(
            reverse("accounts-describe-pack") + "?session=packex00",
            {"pack-pack": str(existing_pack.id), "pack-new_pack": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self._assert_session_value("packex00", "describe_pack", existing_pack.id)
        self.assertNotIsInstance(self.client.session["packex00-describe_pack"], bool)
        self._assert_session_json_safe()

        # New pack -> creates the pack and stores the new pack.id
        resp = self.client.post(
            reverse("accounts-describe-pack") + "?session=packnw00",
            {"pack-pack": PackForm.NEW_PACK_CHOICE_VALUE, "pack-new_pack": "Brand new pack"},
        )
        self.assertEqual(resp.status_code, 302)
        new_pack = Pack.objects.get(user=user, name="Brand new pack")
        self._assert_session_value("packnw00", "describe_pack", new_pack.id)
        self.assertNotIsInstance(self.client.session["packnw00-describe_pack"], bool)
        self._assert_session_json_safe()

        # No pack -> stores the False sentinel (must be the bool False, not an int id)
        resp = self.client.post(
            reverse("accounts-describe-pack") + "?session=packno00",
            {"pack-pack": PackForm.NO_PACK_CHOICE_VALUE, "pack-new_pack": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIs(self.client.session["packno00-describe_pack"], False)
        self._assert_session_json_safe()

    def test_edit_flow_session_is_json_safe(self):
        user, _packs, sounds = create_user_and_sounds(
            num_sounds=2,
            num_packs=0,
            processing_state="OK",
            moderation_state="OK",
        )
        self.client.force_login(user)

        # Select sounds for editing from manage_sounds/published -> writes edit_sounds, len_original_edit_sounds
        resp = self.client.post(
            reverse("accounts-manage-sounds", args=["published"]),
            {"edit": "edit", "object-ids": ",".join(str(s.id) for s in sounds)},
        )
        self.assertEqual(resp.status_code, 302)
        # The edit redirect appends `&session=<prefix>` after `next=`, so split defensively.
        session_key_prefix = resp.url.split("session=")[1].split("&")[0]
        edit_sounds = self.client.session[f"{session_key_prefix}-edit_sounds"]
        self.assertTrue(
            all(isinstance(i, int) and not isinstance(i, bool) for i in edit_sounds),
            f"edit_sounds should be a list of int ids, got {edit_sounds!r}",
        )
        self.assertEqual(sorted(edit_sounds), sorted(s.id for s in sounds))
        self._assert_session_value(session_key_prefix, "len_original_edit_sounds", len(sounds))
        self._assert_session_json_safe()
