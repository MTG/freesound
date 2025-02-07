from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from fscollections import models

# Create your tests here.
class CollectionTest(TestCase):
    
    def test_collections_create_and_delete(self):
        user = User.objects.create_user(username='testuser')
        collection = models.Collection.objects.create(user=user, name='testcollection')
        self.assertEqual(collection.user, user)
        self.assertEqual(collection.name, 'testcollection')
        
        # User not logged in
        # For this to be truly useful, collection urls should be moved into accounts
        # This might have consequences for the way collections work
        resp = self.client.get(reverse('collections'))
        self.assertEqual(302, resp.status_code)

        # Force login and test collections page
        self.client.force_login(user)
        resp = self.client.get(reverse('collections'))
        self.assertEqual(resp.status_code, 200)

        # User logged in, redirect to collections/collection page
        resp = self.client.get(reverse('collections', kwargs={'collection_id': collection.id}))
        self.assertEqual(resp.status_code, 200)

        # Delete collection view
        resp = self.client.get(reverse('delete-collection', kwargs={'collection_id': collection.id}))
        self.assertEqual(resp.status_code, 302)

        # Test collection URL for collection.id does not exist
        resp = self.client.get(reverse('collections', kwargs={'collection_id': 100}))
        self.assertEqual(resp.status_code, 404)

        # Test collection URL with no collection id
        resp = self.client.get(reverse('collections'))
        self.assertEqual(resp.status_code, 200)

    # def test_add_sound_to_collection(self):

    # def test_remove_sound_from_collection(self):

