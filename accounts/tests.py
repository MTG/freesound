'''
Created on Apr 14, 2011

@author: stelios
'''
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
