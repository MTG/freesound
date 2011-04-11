'''
Created on Apr 11, 2011

@author: stelios
'''

from django.test import TestCase
from django.test.client import Client
from tags.models import FS1Tag
from django.core.urlresolvers import reverse

class OldTagLinksRedirectTestCase(TestCase):
    
    fixtures = ['fs1tags.json']
    
    def setUp(self):
        self.client = Client()
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