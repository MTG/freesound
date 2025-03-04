from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from utils.test_helpers import create_user_and_sounds
from fscollections.models import *

# Create your tests here.
class CollectionTest(TestCase):
    
    fixtures = ['licenses', 'sounds']

    def setUp(self):
        self.user = User.objects.create(username='testuser', email='testuser@freesound.org')
        ___, ___, sounds = create_user_and_sounds(num_sounds=3, user=self.user, processing_state="OK", moderation_state="OK")
        self.sound = sounds[0]
        self.collection = Collection(user=self.user, name='testcollection')
        self.collection.save()


    def test_collections_create_and_delete(self):        

        # User not logged in - redirects to login page
        # For this to be truly useful, collection urls should be moved into accounts
        # This might have consequences for the way collections work
        resp = self.client.get(reverse('collections'))
        self.assertEqual(resp.status_code, 302)

        # Force login and test collections page
        self.client.force_login(self.user)
        resp = self.client.get(reverse('collections'))
        self.assertEqual(resp.status_code, 200)

        # User logged in, check given collection id works
        resp = self.client.get(reverse('collections', args=[self.collection.id]))
        self.assertEqual(resp.status_code, 200)

        # Create collection view    
        resp = self.client.post(reverse('create-collection'), {'name': 'tbdcollection'})
        self.assertEqual(resp.status_code, 200) 
        delete_collection = Collection.objects.get(name='tbdcollection')

        # Delete collection view
        resp = self.client.get(reverse('delete-collection',args=[delete_collection.id]))
        self.assertEqual(resp.status_code, 302)

        # Test collection URL for collection.id does not exist
        resp = self.client.get(reverse('collections', args=[delete_collection.id]))
        self.assertEqual(resp.status_code, 404)

    def test_add_remove_sounds(self):
        self.client.force_login(self.user)

        # Test adding sound to collection
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]), {'collection': self.collection.id})
        self.collection.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, self.collection.num_sounds)

        # Test removing sound from collection
        collectionsound = CollectionSound.objects.get(collection=self.collection, sound=self.sound)
        resp = self.client.post(reverse('delete-sound-from-collection', args=[collectionsound.id]))
        self.collection.refresh_from_db()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(0, self.collection.num_sounds)

        # Test edit collection URL
        resp = self.client.get(reverse('edit-collection', args=[self.collection.id]))
        self.assertEqual(resp.status_code, 200)

        # Test download collection
        resp = self.client.get(reverse('download-collection', args=[self.collection.id]))
        self.assertEqual(resp.status_code, 200)