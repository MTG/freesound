import base64
import hashlib
from unittest import mock

from django.test import TestCase, override_settings

from utils.cdn import generate_cdn_download_url
from utils.test_helpers import create_user_and_sounds

CDN_TEST_SETTINGS = {
    "USE_CDN_FOR_DOWNLOADS": True,
    "CDN_SECURE_LINK_SECRET": "test-secret-key",
    "CDN_DOWNLOAD_URL_LIFETIME": 3600,
    "CDN_DOWNLOADS_BASE_URL": "https://cdn.freesound.org",
}


@override_settings(**CDN_TEST_SETTINGS)
class GenerateCdnDownloadUrlTestCase(TestCase):
    fixtures = ["licenses"]

    def setUp(self):
        _, _, sounds = create_user_and_sounds(num_sounds=1)
        self.sound = sounds[0]
        self.sound.moderation_state = "OK"
        self.sound.processing_state = "OK"
        self.sound.save()

    @mock.patch("utils.cdn.create_cdn_symlink")
    @mock.patch("utils.cdn.os.path.exists", return_value=True)
    def test_generates_signed_url_with_correct_params(self, mock_exists, mock_create_symlink):
        url = generate_cdn_download_url(self.sound)
        self.assertIsNotNone(url)
        self.assertIn("cdn.freesound.org", url)
        self.assertIn("md5=", url)
        self.assertIn("expires=", url)
        self.assertIn("filename=", url)

    @mock.patch("utils.cdn.create_cdn_symlink")
    @mock.patch("utils.cdn.os.path.exists", return_value=True)
    @mock.patch("utils.cdn.time.time", return_value=1700000000)
    def test_md5_matches_nginx_secure_link_format(self, mock_time, mock_exists, mock_create_symlink):
        """Verify the generated MD5 matches what nginx secure_link would compute."""
        url = generate_cdn_download_url(self.sound)

        # Extract the md5 and expires from the generated URL
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        md5_from_url = params["md5"][0]
        expires_from_url = params["expires"][0]

        # Recompute using the same formula nginx uses
        uri = parsed.path
        secret = CDN_TEST_SETTINGS["CDN_SECURE_LINK_SECRET"]
        string_to_sign = f"{expires_from_url}{uri}{secret}"
        expected_md5 = hashlib.md5(string_to_sign.encode()).digest()
        expected_base64 = base64.urlsafe_b64encode(expected_md5).rstrip(b"=").decode()

        self.assertEqual(md5_from_url, expected_base64)
        self.assertEqual(expires_from_url, str(1700000000 + 3600))

    @mock.patch("utils.cdn.os.path.exists", return_value=False)
    def test_returns_none_when_file_missing(self, mock_exists):
        url = generate_cdn_download_url(self.sound)
        self.assertIsNone(url)

    @mock.patch("utils.cdn.create_cdn_symlink")
    @mock.patch("utils.cdn.os.path.exists", return_value=True)
    def test_url_contains_folder_and_sound_id_without_user_id(self, mock_exists, mock_create_symlink):
        url = generate_cdn_download_url(self.sound)
        path = url.split("?")[0]
        folder_id = str(self.sound.id // 1000)
        # URI should be /sounds/{folder}/{sound_id}.{type} — no user_id
        self.assertIn(f"/sounds/{folder_id}/{self.sound.id}.{self.sound.type}", path)
        self.assertNotIn(f"_{self.sound.user_id}.", path)
