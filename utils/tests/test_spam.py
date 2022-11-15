from unittest import skipIf

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from utils.spam import is_spam


class SpamTest(TestCase):
    def setUp(self):
        spam_user = User.objects.create_user(
            username="viagra-test-123", email="akismet-guaranteed-spam@example.com"
        )
        self.client.force_login(spam_user)
        rf = RequestFactory()
        self.spam_request = rf.post("/some_form/")
        self.spam_request.user = spam_user

    @skipIf(not settings.AKISMET_KEY, "No Akismet API key set.")
    def test_spam(self):
        self.assertTrue(is_spam(self.spam_request, ""))
