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

from django.test import TestCase
from django.urls import reverse

from tags.models import FS1Tag


class OldTagLinksRedirectTestCase(TestCase):
    
    fixtures = ['fs1tags']
    
    def setUp(self):
        self.fs1tags = [tag.fs1_id for tag in FS1Tag.objects.all()[0:2]]
        
    def test_old_tag_link_redirect_single_ok(self):
        # 301 permanent redirect, single tag result exists
        response = self.client.get(reverse('old-tag-page'), data={'id' : self.fs1tags[0]})
        self.assertEqual(response.status_code, 301)
    
    def test_old_tag_link_redirect_multi_ok(self):    
        # 301 permanent redirect, multiple tags result exists
        ids = '_'.join([ str(temp) for temp in self.fs1tags])
        response = self.client.get(reverse('old-tag-page'), data={'id' : ids})
        self.assertEqual(response.status_code, 301)
        
    def test_old_tag_link_redirect_partial_ids_list(self):
        # 301 permanent redirect, one of the tags in the list exists
        partial_ids = str(self.fs1tags[0]) + '_0'
        response = self.client.get(reverse('old-tag-page'), data={'id' : partial_ids})
        self.assertEqual(response.status_code, 301)    
        
    def test_old_tag_link_redirect_not_exists_id(self):
        # 404 id exists does not exist
        response = self.client.get(reverse('old-tag-page'), data={'id' : 0}, follow=True)
        self.assertEqual(response.status_code, 404)
        
    def test_old_tag_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse('old-tag-page'), data={'id' : 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)    
        
    def test_old_tag_link_redirect_partial_invalid_id(self):
        # 404 invalid id in the id list
        partial_ids = str(self.fs1tags[0]) + '_invalidValue'
        response = self.client.get(reverse('old-tag-page'), data={'id' : partial_ids}, follow=True)
        self.assertEqual(response.status_code, 404) 
