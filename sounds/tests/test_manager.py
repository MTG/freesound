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

from django.conf import settings
from django.test import TestCase

from sounds.models import Sound, Pack
from tickets.models import Ticket
from utils.test_helpers import (
    create_user_and_sounds,
    create_consolidated_audio_descriptors_and_similarity_vectors_for_sound,
)


class SoundManagerQueryMethods(TestCase):
    fixtures = ["licenses"]

    fields_to_check_bulk_query_id = [
        "username",
        "id",
        "type",
        "user_id",
        "original_filename",
        "is_explicit",
        "avg_rating",
        "num_ratings",
        "description",
        "moderation_state",
        "processing_state",
        "processing_ongoing_state",
        "similarity_state",
        "created",
        "num_downloads",
        "num_comments",
        "pack_id",
        "duration",
        "pack_name",
        "license_id",
        "remixgroup_id",
        "tag_array",
    ]
    fields_to_check_related = ["user", "pack", "license", "ticket"]
    fields_to_check_subqueries = [
        "consolidated_audio_descriptors",
        "similarity_vectors",
        "analysis_state_essentia_exists",
        "ready_for_similarity_precomputed",
    ]

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=3, num_packs=1, tags="tag1 tag2 tag3")
        for sound in sounds:
            create_consolidated_audio_descriptors_and_similarity_vectors_for_sound(sound)

        self.sound_ids = [s.id for s in sounds]
        self.user = user
        self.pack = packs[0]

    def test_bulk_query_id_num_queries(self):
        for sound_id in self.sound_ids:
            Ticket.objects.create(sender=self.user, sound_id=sound_id)

        # Check that all fields for each sound are retrieved with one query + one for the analyzers
        with self.assertNumQueries(1):
            has_at_least_one_geotag = False
            for sound in Sound.objects.bulk_query_id(
                sound_ids=self.sound_ids, include_audio_descriptors=True, include_similarity_vectors=True
            ):
                if hasattr(sound, "geotag"):
                    # We do this separately, because a OneToOneField needs to be checked by "getattr", and it'll
                    # raise an AttributeError if the field is not present. Therefore we just check that at least one
                    # sound has a geotag.
                    has_at_least_one_geotag = True

                for field in self.fields_to_check_bulk_query_id:
                    self.assertTrue(hasattr(sound, field), f"Missing field {field} in sound {sound.id}")
                for field in self.fields_to_check_related:
                    self.assertTrue(hasattr(sound, field), f"Missing field {field} in sound {sound.id}")
                for field in self.fields_to_check_subqueries:
                    self.assertTrue(hasattr(sound, field), f"Missing field {field} in sound {sound.id}")

                # Check that accessing the audio features and similarity vectors does not raise additional queries
                for feature_name in settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES:
                    sound.get_consolidated_analysis_data()[feature_name]
                for similarity_space_name in settings.SIMILARITY_SPACES_NAMES:
                    sound.get_similarity_vector(similarity_space_name=similarity_space_name)

            self.assertTrue(has_at_least_one_geotag, "No geotag found in any of the sounds")

    def test_bulk_query_id_field_contents(self):
        # Check the contents of some fields are correct
        for sound in Sound.objects.bulk_query_id(
            sound_ids=self.sound_ids, include_audio_descriptors=True, include_similarity_vectors=True
        ):
            self.assertEqual(Sound.objects.get(id=sound.id).user.username, sound.username)
            self.assertEqual(Sound.objects.get(id=sound.id).original_filename, sound.original_filename)
            self.assertEqual(Sound.objects.get(id=sound.id).pack_id, sound.pack_id)
            self.assertEqual(Sound.objects.get(id=sound.id).license_id, sound.license_id)
            self.assertCountEqual(Sound.objects.get(id=sound.id).get_sound_tags(), sound.tag_array)

    def test_ordered_ids(self):
        # This method is similar to SoundManager.bulk_query_id but returns the sounds in the same order as the
        # the IDs in sound_ids. Here we only check that the sorting is correct. (the other things like returned
        # sound fields being correct are already tested in previous tests).
        with self.assertNumQueries(1):
            for i, sound in enumerate(Sound.objects.ordered_ids(sound_ids=self.sound_ids)):
                self.assertEqual(self.sound_ids[i], sound.id)

    def test_bulk_sounds_for_user(self):
        # This method uses SoundManager.bulk_query internally (also used by SoundManager.bulk_query_id) to retrieve
        # sounds by a user. We only check that filtering by user works here (the other things like returned sound fields
        # being correct are already tested in previous tests).

        # Created sounds are not yet moderated and processed ok, so bulk_sounds_for_user should return no sounds
        self.assertEqual(len(list(Sound.objects.bulk_sounds_for_user(user_id=self.user.id))), 0)

        # Now we set user sounds to moderated and processed ok (and set user_sound_ids for later use)
        user_sound_ids = []
        for sound in Sound.objects.filter(user=self.user):
            sound.moderation_state = "OK"
            sound.processing_state = "OK"
            sound.save()
            user_sound_ids.append(sound.id)

        # Check that now sounds returned by bulk_sounds_for_user are ok
        user_sound_ids_bulk_query = []
        with self.assertNumQueries(1):
            for i, sound in enumerate(Sound.objects.bulk_sounds_for_user(user_id=self.user.id)):
                self.assertEqual(self.user.id, sound.user_id)
                user_sound_ids_bulk_query.append(sound.id)
        self.assertCountEqual(user_sound_ids, user_sound_ids_bulk_query)

    def test_bulk_sounds_for_pack(self):
        # This method uses SoundManager.bulk_query internally (also used by SoundManager.bulk_query_id) to retrieve
        # sounds of a pack. We only check that filtering by pack works here (the other things like returned sound fields
        # being correct are already tested in previous tests).

        # Created sounds are not yet moderated and processed ok, so bulk_sounds_for_pack should return no sounds
        self.assertEqual(len(list(Sound.objects.bulk_sounds_for_pack(pack_id=self.pack.id))), 0)

        # Now we set user sounds to moderated and processed ok (and set pack_sound_ids for later use)
        pack_sound_ids = []
        for sound in Sound.objects.filter(pack=self.pack):
            sound.moderation_state = "OK"
            sound.processing_state = "OK"
            sound.save()
            pack_sound_ids.append(sound.id)

        # Check that now sounds returned by bulk_sounds_for_pack are ok
        pack_sound_ids_bulk_query = []
        with self.assertNumQueries(1):
            for i, sound in enumerate(Sound.objects.bulk_sounds_for_pack(pack_id=self.pack.id)):
                self.assertEqual(self.user.id, sound.user_id)
                pack_sound_ids_bulk_query.append(sound.id)
        self.assertCountEqual(pack_sound_ids, pack_sound_ids_bulk_query)


class PublicSoundManagerTest(TestCase):
    fixtures = ["licenses", "sounds"]

    def test_public_sounds(self):
        # Sounds.public manager only selects sounds which have
        # processing state and moderation state set to OK
        all_sounds = Sound.objects.all()
        public_sounds = Sound.public.all()

        self.assertEqual(len(all_sounds), len(public_sounds))

        s1 = all_sounds[0]
        s2 = all_sounds[1]
        s1.processing_state = "PE"
        s1.save()
        s2.moderation_state = "PE"
        s2.save()

        all_sounds = Sound.objects.all()
        public_sounds = Sound.public.all()

        self.assertEqual(len(all_sounds), len(public_sounds) + 2)


class PackManagerQueryMethods(TestCase):
    fixtures = ["licenses"]

    fields_to_check_bulk_query_id = [
        "id",
        "user_id",
        "name",
        "description",
        "is_dirty",
        "created",
        "license_crc",
        "last_updated",
        "num_downloads",
        "num_sounds",
        "is_deleted",
    ]

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=3, num_packs=3, tags="tag1 tag2 tag3")
        self.pack_ids = [p.id for p in packs]
        self.user = user

    def test_ordered_ids(self):
        # Test that ordered_ids returns a sorted list of Pack objects with the requested IDs, including duplicates
        with self.assertNumQueries(2):
            pack_ids_with_duplicates = self.pack_ids + self.pack_ids
            for i, pack in enumerate(Pack.objects.ordered_ids(pack_ids=pack_ids_with_duplicates)):
                self.assertEqual(type(pack), Pack)
                self.assertEqual(pack_ids_with_duplicates[i], pack.id)
