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
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from accounts.forms import RecaptchaForm
from accounts.models import Profile


class OldUserLinksRedirectTestCase(TestCase):
    
    fixtures = ['users.json']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.all()[0]
        
    def test_old_user_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        resp = self.client.get(reverse('old-account-page'), data={'id': self.user.id})
        self.assertEqual(resp.status_code, 301)
        
    def test_old_user_link_redirect_not_exists_id(self):
        # 404 id does not exist
        resp = self.client.get(reverse('old-account-page'), data={'id': 0}, follow=True)
        self.assertEqual(resp.status_code, 404)
        
    def test_old_user_link_redirect_invalid_id(self):
        # 404 invalid id
        resp = self.client.get(reverse('old-account-page'), data={'id': 'invalid_id'}, follow=True)
        self.assertEqual(resp.status_code, 404)


class UserRegistrationAndActivation(TestCase):

    fixtures = ['users.json']

    def test_user_registration(self):
        RecaptchaForm.validate_captcha = lambda x: True  # Monkeypatch recaptcha validation so the form validates
        resp = self.client.post("/home/register/", {'username': 'testuser',
                                                    'first_name': 'test_first_name',
                                                    'last_name': 'test_last_name',
                                                    'email1': 'email@example.com',
                                                    'email2': 'email@example.com',
                                                    'password1': 'testpass',
                                                    'password2': 'testpass',
                                                    'newsletter': '1',
                                                    'accepted_tos': '1',
                                                    'recaptcha_challenge_field': 'a',
                                                    'recaptcha_response_field': 'a'})

        self.assertEqual(resp.status_code, 200)

        u = User.objects.get(username='testuser')
        self.assertEqual(u.profile.wants_newsletter, True)  # Check profile parameters are set correctly
        self.assertEqual(u.profile.accepted_tos, True)

        u.is_active = True  # Set user active and check it can login
        u.save()
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get("/home/")
        self.assertEqual(resp.status_code, 200)

    def test_user_save(self):
        u = User.objects.create_user("testuser2", password="testpass")
        self.assertEqual(Profile.objects.filter(user=u).count() > 0, True)
        u.save()  # Check saving user again (with existing profile) does not fail

    def test_user_activation(self):
        user = User.objects.get(username="User6Inactive")  # Inactive user in fixture

        # Test calling accounts-activate with wrong hash, user should not be activated
        bad_hash = '4dad3dft'
        resp = self.client.get(reverse('accounts-activate', args=[user.username, bad_hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['decode_error'], True)
        self.assertEqual(User.objects.get(username="User6Inactive").is_active, False)

        # Test calling accounts-activate with good hash, user should be activated
        from utils.encryption import create_hash
        hash = create_hash(user.id)
        resp = self.client.get(reverse('accounts-activate', args=[user.username, hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['all_ok'], True)
        self.assertEqual(User.objects.get(username="User6Inactive").is_active, True)

        # Test calling accounts-activate for a user that does not exist
        resp = self.client.get(reverse('accounts-activate', args=["noone", hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['user_does_not_exist'], True)


