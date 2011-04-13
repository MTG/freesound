'''
Created on Apr 8, 2011

@author: stelios
'''
from django.test import TestCase, Client
from sounds.models import Sound, Pack
from django.core.urlresolvers import reverse

# Test old sound links redirect
class OldSoundLinksRedirectTestCase(TestCase):
    
    fixtures = ['sounds.json']
    
    def setUp(self):
        self.client = Client()
        self.sound = Sound.objects.all()[0]
        
    def test_old_sound_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        response = self.client.get(reverse('old-sound-page'), data={'id' : self.sound.id})
        self.assertEqual(response.status_code, 301)
        
    def test_old_sound_link_redirect_not_exists_id(self):
        # 404 id does not exist
        response = self.client.get(reverse('old-sound-page'), data={'id' : 0}, follow=True)
        self.assertEqual(response.status_code, 404)
        
    def test_old_sound_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse('old-sound-page'), data={'id' : 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)    

# Test old pack links redirect
class OldPackLinksRedirectTestCase(TestCase):
    
    fixtures = ['packs.json']
            
    def setUp(self):
        self.client = Client()
        self.pack = Pack.objects.all()[0]
                    
    def test_old_pack_link_redirect_ok(self):
        response = self.client.get(reverse('old-pack-page'), data={'id' : self.pack.id})
        self.assertEqual(response.status_code, 301)
        
        
    def test_old_pack_link_redirect_not_exists_id(self):
        response = self.client.get(reverse('old-pack-page'), data={'id' : 0}, follow=True)
        self.assertEqual(response.status_code, 404)
        
        
    def test_old_pack_link_redirect_invalid_id(self):
        response = self.client.get(reverse('old-pack-page'), data={'id' : 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)