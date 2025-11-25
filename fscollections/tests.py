from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse

from utils.test_helpers import create_user_and_sounds
from fscollections.models import Collection


class CollectionTest(TestCase):
    
    fixtures = ['licenses', 'sounds']

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@freesound.org')
        self.maintainer = User.objects.create_user(username='maintaineruser', email='maintainer@freesound.org')
        self.external_user = User.objects.create_user(username='external_user', email='externaluser@freesound.org')
        _, _, sounds = create_user_and_sounds(num_sounds=3, user=self.user, processing_state="OK", moderation_state="OK")
        self.sound = sounds[0]
        self.sound1 = sounds[1]
        self.sound2 = sounds[2]
        self.collection = Collection.objects.create(user=self.user, name='testcollection')

    def test_collections_create_and_delete(self):        

        # User not logged in - redirects to login page
        # For this to be truly useful, collection urls should be moved into accounts
        # This might have consequences for the way collections work
        resp = self.client.get(reverse('your-collections'))
        self.assertEqual(resp.status_code, 302)

        # Force login and test collections page
        self.client.force_login(self.user)
        resp = self.client.get(reverse('your-collections'))
        self.assertEqual(resp.status_code, 200)

        # User logged in, check given collection id works
        resp = self.client.get(reverse('collection', args=[self.collection.id]))
        self.assertEqual(resp.status_code, 200)

        # Create collection view    
        resp = self.client.post(reverse('create-collection')+'?ajax=1', {'name': 'tbdcollection'})
        self.assertEqual(resp.status_code, 200) 
        delete_collection = Collection.objects.get(name='tbdcollection')

        # Delete collection view
        resp = self.client.post(reverse('delete-collection',args=[delete_collection.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual("/collections/", resp.url)

        # Test collection URL for collection.id does not exist
        resp = self.client.get(reverse('collection', args=[delete_collection.id]))
        self.assertEqual(resp.status_code, 404)

    def test_add_remove_sounds_as_user(self):
        # test edit collection's parameters as owner of the collection
        # collection edit should include: adding and removing sounds, editing collection's name (consider bookmark's restriction)
        # editing description and visibility and adding and removing maintainers
        # bear in mind that sounds can be added from edit url and through adding sounds modal
        self.client.force_login(self.user)

        # Test adding sound to collection
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', {'collection': self.collection.id})
        self.collection.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, self.collection.num_sounds)

        # Test adding the same sound again and check for num_sounds to ensure it's not duplicated
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', {'collection': self.collection.id})
        self.assertEqual(200, resp.status_code)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.num_sounds)

        # Test creating the default collection using the add_sound_to_collection modal
        form_data = {'collection': -1, 'new_collection_name': '', 'use_last_collection': False}
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        default_collection = Collection.objects.get(user=self.user, name="Bookmarks", is_default_collection=True)
        resp = self.client.get(reverse('collection', args=[default_collection.id]))
        self.assertEqual(200, resp.status_code)

        # Test creating a new custom collection using the add_sound_to_collection modal
        form_data = {'collection': 0, 'new_collection_name': 'new_collection', 'use_last_collection': False}
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        new_collection = Collection.objects.get(user=self.user, name="new_collection")
        self.assertEqual(1, new_collection.num_sounds)

        # Test download collection
        resp = self.client.get(reverse('download-collection', args=[self.collection.id]))
        self.assertEqual(resp.status_code, 200)
    
    def test_add_remove_sounds_as_maintainer(self):
        # test edit collection's parameters as maintainer of the collection
        self.collection.maintainers.add(self.maintainer)
        self.collection.refresh_from_db()

        self.client.force_login(self.maintainer)

        # Test adding sound to collection as a maintainer
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]), {'collection': self.collection.id})
        self.collection.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, self.collection.num_sounds)

        # Test adding the same sound again and check for num_sounds to ensure it's not duplicated
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', {'collection': self.collection.id})
        self.assertEqual(200, resp.status_code)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.num_sounds)

        # Test adding sound to a collection where request user is not a maintainer (not valid)
        maintainer_test_collection = Collection.objects.create(name="maintainer_test_collection", user=self.user)
        form_data = {'collection': maintainer_test_collection.id, 'new_collection_name': '', 'use_last_collection': False}
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        maintainer_test_collection.refresh_from_db()
        self.assertEqual(0, maintainer_test_collection.num_sounds)

        # Test deleting a collection where request user is maintainer (not valid)
        resp = self.client.post(reverse('delete-collection',args=[self.collection.id]))
        messages = list(get_messages(resp.wsgi_request))
        self.assertTrue(len(messages)>0)
        self.assertEqual(str(messages[0]), "You're not allowed to delete this collection."
                             "In order to delete a collection you must be the owner.")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)

    def test_add_remove_sounds_as_external_user(self):
        self.client.force_login(self.external_user)

        # Test adding sound to collection as external user (not owner nor maintainer -> shouldn't be added)
        resp = self.client.post(reverse('add-sound-to-collection', args=[self.sound.id]), {'collection': self.collection.id})
        self.collection.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        response_data = resp.json()
        self.assertEqual(response_data['success'], False)
        self.assertEqual(0, self.collection.num_sounds)

        # Additionally, test edit URL for external user
        resp = self.client.get(reverse('edit-collection', args=[self.collection.id]))
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)

        # Test deleting a collection as an external user (not owner -> not valid)
        resp = self.client.post(reverse('delete-collection',args=[self.collection.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)

    def test_edit_collection_as_user(self):
        # Test the edit collection form submission for different case scenarios
        self.client.force_login(self.user)
        edit_collection = Collection.objects.create(user=self.user, name='edited-collection')

        # Test setting an already existing name for a collection (form should be invalid therefore, the name should not change)
        form_data = {'name': 'testcollection', 'description':'', 'public': False}
        resp = self.client.post(reverse('edit-collection', args=[edit_collection.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        edit_collection.refresh_from_db()
        self.assertEqual('edited-collection',edit_collection.name)

        # Test setting 'Bookmarks' as the name for a collection (form should be invalid therefore, the name should not change)
        form_data = {'name': 'Bookmarks', 'description':'', 'public': False}
        resp = self.client.post(reverse('edit-collection', args=[edit_collection.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        edit_collection.refresh_from_db()
        self.assertEqual('edited-collection',edit_collection.name)

        # Test creating the default collection and trying to change its name and public parameters (both are static)
        default_collection = Collection.objects.create(name='Bookmarks', user=self.user, is_default_collection=True)
        form_data = {'name': 'other-name', 'description':'', 'public': True}
        resp = self.client.post(reverse('edit-collection', args=[default_collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{default_collection.id}/", resp.url)
        default_collection.refresh_from_db()
        self.assertEqual('Bookmarks', default_collection.name)
        self.assertEqual('', default_collection.description)
        self.assertEqual(False, default_collection.public)

        # Test adding and removing maintainers from edit URL
        # Add maintainers and avoid duplicates
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'maintainers': f"{self.maintainer.id},{self.external_user.id},{self.maintainer.id}"}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(2, self.collection.maintainers.all().count())
        # Remove maintainer
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'maintainers': f"{self.maintainer.id}"}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.maintainers.all().count())

        # Test adding and removing sounds from edit URL
        # Add sounds and avoid duplicates
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'collection_sounds': f"{self.sound.id},{self.sound1.id},{self.sound.id}"}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(2, self.collection.num_sounds)
        # Remove sound
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'collection_sounds': f"{self.sound.id}"}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.num_sounds)

        # Test adding more sounds than permitted
        ___, ___, added_sounds = create_user_and_sounds(num_sounds=settings.MAX_SOUNDS_PER_COLLECTION + 1, count_offset=3 ,user=self.user, processing_state="OK", moderation_state="OK")
        sounds_ids = ','.join([str(s.id) for s in added_sounds])
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'collection_sounds': sounds_ids}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(200, resp.status_code)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.num_sounds)
        
    def test_edit_collection_as_maintainer(self):
        # available fields for a maintainer: sounds
        self.collection.maintainers.add(self.maintainer)
        self.collection.refresh_from_db()

        self.client.force_login(self.maintainer)

        # Test adding and removing sounds from edit URL
        form_data = {'name': 'testcollection', 'description':'', 'public': False, 'collection_sounds': str(self.sound.id)}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(1, self.collection.num_sounds)
        form_data.pop('collection_sounds')
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual(0, self.collection.num_sounds)

        # Test changes in other fields
        form_data = {'name': 'other-name', 'description':'changed', 'public': True, 'maintainers': str(self.external_user.id)}
        resp = self.client.post(reverse('edit-collection', args=[self.collection.id]) + '?ajax=1', form_data)
        self.assertEqual(302, resp.status_code)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.collection.refresh_from_db()
        self.assertEqual('testcollection', self.collection.name)
        self.assertEqual('', self.collection.description)
        self.assertEqual(False, self.collection.public)
        self.assertEqual(1, self.collection.maintainers.all().count())

        # Test collection deletion as maintainer
        resp = self.client.get(reverse('delete-collection',args=[self.collection.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(f"/collections/{self.collection.id}/", resp.url)
        self.assertTrue(Collection.objects.filter(id=self.collection.id).exists())
        