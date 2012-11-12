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

# Test old user links redirect
class OldUserLinksRedirectTestCase(TestCase):
    
    fixtures = ['users.json']
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.all()[0]
        
    def test_old_user_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        response = self.client.get(reverse('old-account-page'), data={'id' : self.user.id})
        self.assertEqual(response.status_code, 301)
        
    def test_old_user_link_redirect_not_exists_id(self):
        # 404 id does not exist
        response = self.client.get(reverse('old-account-page'), data={'id' : 0}, follow=True)
        self.assertEqual(response.status_code, 404)
        
    def test_old_user_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse('old-account-page'), data={'id' : 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)    
