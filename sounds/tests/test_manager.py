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

from geotags.models import GeoTag
from sounds.models import License, Pack, Sound, SoundSimilarityVector
from tickets.models import Ticket
from utils.test_helpers import (
    create_consolidated_audio_descriptors_and_similarity_vectors_for_sound,
    create_user_and_sounds,
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
        "ready_for_similarity_precomputed",
    ]

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=3, num_packs=1, tags="tag1 tag2 tag3")
        GeoTag.objects.create(sound=sounds[0], lat=1.0, lon=1.0, zoom=1)
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

    @staticmethod
    def _make_sound(
        user,
        pack,
        original_filename,
        *,
        license=None,
        num_ratings=0,
        avg_rating=0.0,
        tags=None,
        processing_state="OK",
        moderation_state="OK",
    ):
        """Create a Sound in a pack (public by default) with tweakable fields."""
        sound = Sound.objects.create(
            user=user,
            original_filename=original_filename,
            license=license or License.objects.last(),
            bst_category="ss-n",
            description="",
            pack=pack,
            md5=f"fake{original_filename}",
            type="wav",
            num_ratings=num_ratings,
            avg_rating=avg_rating,
            processing_state=processing_state,
            moderation_state=moderation_state,
        )
        if tags is not None:
            sound.set_tags(tags)
        return sound

    def test_ordered_ids(self):
        # Test that ordered_ids returns a sorted list of Pack objects with the requested IDs, including duplicates.
        # After the bulk_query_id rewrite the query count is 3:
        #   1. Pack queryset with annotated subqueries (totals/ratings/has_geotag/license_pairs)
        #   2. Window query for top-N sounds per pack
        #   3. SoundTag aggregate for top-10 tags per pack
        # The SoundSimilarityVector check (Query 4 in the implementation) is skipped because
        # Django optimizes filter(...__in=[]) to no SQL when no sounds were selected.
        # This holds only while none of the fixture sounds are public: the public-filtered
        # Window/Tag queries return zero rows and no sound is selected. Assert that
        # precondition explicitly so a fixture change fails here rather than as an opaque
        # query-count mismatch.
        self.assertEqual(Sound.public.filter(pack_id__in=self.pack_ids).count(), 0)
        with self.assertNumQueries(3):
            pack_ids_with_duplicates = self.pack_ids + self.pack_ids
            for i, pack in enumerate(Pack.objects.ordered_ids(pack_ids=pack_ids_with_duplicates)):
                self.assertEqual(type(pack), Pack)
                self.assertEqual(pack_ids_with_duplicates[i], pack.id)

    def test_bulk_query_id_num_sounds_unpublished(self):
        # some published and some unpublished sounds result in num_sounds_unpublished_precomputed
        # being set properly
        _, packs, _ = create_user_and_sounds(
            num_sounds=2, num_packs=1, user=self.user, count_offset=100, processing_state="OK", moderation_state="OK"
        )
        pack = packs[0]
        self._make_sound(self.user, pack, "unpublished sound", processing_state="PE", moderation_state="PE")
        pack.process()
        self.assertEqual(pack.num_sounds, 2)
        p = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertEqual(p.num_sounds_unpublished_precomputed, 1)

    def test_bulk_query_id_synthetic_parity(self):
        # Build a pack with: 5 public sounds (varying licenses + tags + ratings + one geotag),
        # plus 1 unpublished sound. Verify every precomputed attr matches expectations.
        pack = Pack.objects.create(user=self.user, name="parity pack")
        licenses = list(License.objects.all()[:2])
        self.assertGreaterEqual(len(licenses), 2, "need at least 2 licenses fixture-loaded")

        public_sounds = []
        for i in range(5):
            s = self._make_sound(
                self.user,
                pack,
                f"parity-public-{i}",
                license=licenses[i % 2],
                num_ratings=(settings.MIN_NUMBER_RATINGS + i) if i < 3 else 0,
                avg_rating=(6.0 + i) if i < 3 else 0.0,
                tags=["alpha", "beta"] if i < 2 else ["alpha"],
            )
            public_sounds.append(s)

        # 1 unpublished sound
        self._make_sound(
            self.user, pack, "parity-unpublished", license=licenses[0], processing_state="PE", moderation_state="PE"
        )
        # Geotag on one public sound
        GeoTag.objects.create(sound=public_sounds[0], lat=1.0, lon=1.0, zoom=1)

        # Pack.num_sounds tracks public count; set explicitly (Pack.process() would normally maintain this).
        pack.num_sounds = 5
        pack.save()

        result = Pack.objects.bulk_query_id([pack.id])
        self.assertEqual(len(result), 1)
        p = result[0]

        # Three newest public sounds in -created order (id is the tiebreaker).
        expected_top_ids = [s.id for s in sorted(public_sounds, key=lambda s: (s.created, s.id), reverse=True)[:3]]
        self.assertEqual([d["id"] for d in p.selected_sounds_data], expected_top_ids)

        # Each selected sound dict has all expected keys.
        expected_keys = {
            "id",
            "username",
            "ready_for_similarity",
            "duration",
            "preview_mp3",
            "preview_ogg",
            "wave",
            "spectral",
            "num_ratings",
            "avg_rating",
        }
        for d in p.selected_sounds_data:
            self.assertEqual(set(d.keys()), expected_keys)
            self.assertIsInstance(d["ready_for_similarity"], bool)
            self.assertFalse(d["ready_for_similarity"])  # no SoundSimilarityVector rows created

        # ready_for_similarity flips to True for the sound that has a vector and stays False
        # for the others. public_sounds[4] is the newest sound, so it is always in the top-3.
        SoundSimilarityVector.objects.create(
            sound=public_sounds[4],
            similarity_space_name=settings.SIMILARITY_SPACES_NAMES[0],
            vector=[0.0] * settings.SIMILARITY_SPACES[settings.SIMILARITY_SPACES_NAMES[0]]["vector_size"],
        )
        result2 = Pack.objects.bulk_query_id([pack.id])
        ready_flags = {d["id"]: d["ready_for_similarity"] for d in result2[0].selected_sounds_data}
        self.assertTrue(ready_flags[public_sounds[4].id])
        self.assertFalse(ready_flags[public_sounds[3].id])
        self.assertFalse(ready_flags[public_sounds[2].id])

        # num_sounds_unpublished_precomputed = total - public.
        self.assertEqual(p.num_sounds_unpublished_precomputed, 1)

        # licenses_data_precomputed: paired by index, length matches distinct license count.
        license_ids, license_names = p.licenses_data_precomputed
        self.assertEqual(len(license_ids), len(license_names))
        self.assertEqual(set(license_ids), {lic.id for lic in licenses})
        for lid, lname in zip(license_ids, license_names):
            self.assertEqual(License.objects.get(id=lid).name, lname)

        # pack_tags: ≤10 entries, sorted by count desc then name asc.
        self.assertLessEqual(len(p.pack_tags), 10)
        counts = [t["count"] for t in p.pack_tags]
        self.assertEqual(counts, sorted(counts, reverse=True))
        # alpha appears in all 5 public sounds, beta in 2 (i<2). Order: alpha then beta.
        self.assertEqual(p.pack_tags[0]["name"], "alpha")
        self.assertEqual(p.pack_tags[0]["count"], 5)
        self.assertEqual(p.pack_tags[1]["name"], "beta")
        self.assertEqual(p.pack_tags[1]["count"], 2)

        self.assertTrue(p.has_geotags_precomputed)

        # ratings: 3 sounds at/above threshold (i=0,1,2), avg of (6.0, 7.0, 8.0) = 7.0.
        self.assertEqual(p.num_ratings_precomputed, 3)
        self.assertAlmostEqual(p.avg_rating_precomputed, 7.0)

    def test_bulk_query_id_sound_ids_for_pack_id_happy_path(self):
        pack = Pack.objects.create(user=self.user, name="preselect happy")
        sounds = [self._make_sound(self.user, pack, f"pre-{i}") for i in range(4)]
        # sounds are created oldest-first, so sounds[3] is newest. The supplied order is
        # deliberately not newest-first: selected_sounds_data must still come out newest-first.
        preselected = [sounds[0].id, sounds[2].id]

        result = Pack.objects.bulk_query_id([pack.id], sound_ids_for_pack_id={pack.id: preselected})
        self.assertEqual([d["id"] for d in result[0].selected_sounds_data], [sounds[2].id, sounds[0].id])

    def test_bulk_query_id_sound_ids_for_pack_id_missing_raises(self):
        pack_a = Pack.objects.create(user=self.user, name="A")
        pack_b = Pack.objects.create(user=self.user, name="B")
        sound = self._make_sound(self.user, pack_a, "preselect-a")
        # Missing entry for pack_b → ValueError.
        with self.assertRaises(ValueError):
            Pack.objects.bulk_query_id(
                [pack_a.id, pack_b.id],
                sound_ids_for_pack_id={pack_a.id: [sound.id]},
            )

    def test_bulk_query_id_sound_ids_cross_pack_dropped(self):
        pack_a = Pack.objects.create(user=self.user, name="X")
        pack_b = Pack.objects.create(user=self.user, name="Y")
        sound_b = self._make_sound(self.user, pack_b, "y-sound")

        result = Pack.objects.bulk_query_id(
            [pack_a.id, pack_b.id],
            # Both packs list sound_b's id. Only pack_b should keep it; pack_a drops it.
            sound_ids_for_pack_id={pack_a.id: [sound_b.id], pack_b.id: [sound_b.id]},
        )
        by_id = {p.id: p for p in result}
        self.assertEqual(by_id[pack_a.id].selected_sounds_data, [])
        self.assertEqual([d["id"] for d in by_id[pack_b.id].selected_sounds_data], [sound_b.id])

    def test_bulk_query_id_empty_ratings_subquery(self):
        # All public sounds below MIN_NUMBER_RATINGS → ratings_data subquery returns no rows.
        pack = Pack.objects.create(user=self.user, name="no-rated")
        for i in range(2):
            self._make_sound(
                self.user, pack, f"unrated-{i}", num_ratings=max(0, settings.MIN_NUMBER_RATINGS - 1), avg_rating=5.0
            )
        p = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertEqual(p.num_ratings_precomputed, 0)
        self.assertEqual(p.avg_rating_precomputed, 0.0)

    def test_bulk_query_id_window_tiebreaker(self):
        # Two sounds with identical `created` → tiebreak by descending id.
        pack = Pack.objects.create(user=self.user, name="ties")
        s_old = self._make_sound(self.user, pack, "old")
        s_mid_a = self._make_sound(self.user, pack, "mid-a")
        s_mid_b = self._make_sound(self.user, pack, "mid-b")
        s_new = self._make_sound(self.user, pack, "new")
        # Make mid-a and mid-b share the same `created` value.
        Sound.objects.filter(id=s_mid_a.id).update(created=s_mid_b.created)
        s_mid_a.refresh_from_db()

        p = Pack.objects.bulk_query_id([pack.id])[0]
        top_ids = [d["id"] for d in p.selected_sounds_data]
        # `created` ranking: s_new (latest) > {s_mid_a, s_mid_b} (tie) > s_old.
        # Tiebreaker -id puts higher id first among ties.
        higher_mid, lower_mid = sorted([s_mid_a.id, s_mid_b.id], reverse=True)
        self.assertEqual(top_ids, [s_new.id, higher_mid, lower_mid])

    def test_bulk_query_id_has_geotag_only_unpublished(self):
        # A pack whose only geotagged sounds are unpublished must report has_geotags_precomputed=False.
        pack = Pack.objects.create(user=self.user, name="geotag-unpublished-only")
        unpub = self._make_sound(self.user, pack, "unpub-geo", processing_state="PE", moderation_state="PE")
        GeoTag.objects.create(sound=unpub, lat=1.0, lon=1.0, zoom=1)
        # And one public sound without a geotag, so the pack has at least one public row.
        self._make_sound(self.user, pack, "pub-no-geo")

        p = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertFalse(p.has_geotags_precomputed)

    def test_bulk_query_id_pack_tags_bounded_to_top_10(self):
        # The tag query limits to the 10 most-used tags per pack in SQL; ties broken by name.
        pack = Pack.objects.create(user=self.user, name="tag-bound")
        tag_names = [f"tag{i:02d}" for i in range(12)]
        self._make_sound(self.user, pack, "tags-a", tags=tag_names)
        self._make_sound(self.user, pack, "tags-b", tags=["tag11"])

        p = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertEqual(len(p.pack_tags), 10)
        # tag11 appears on both sounds so it ranks first; the rest tie at 1 and sort by name.
        self.assertEqual(p.pack_tags[0]["name"], "tag11")
        self.assertEqual(p.pack_tags[0]["count"], 2)
        self.assertEqual([t["name"] for t in p.pack_tags[1:]], tag_names[:9])

    def test_bulk_query_id_empty_pack(self):
        pack = Pack.objects.create(user=self.user, name="empty")
        p = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertEqual(p.selected_sounds_data, [])
        self.assertEqual(p.num_sounds_unpublished_precomputed, 0)
        self.assertEqual(p.licenses_data_precomputed, ([], []))
        self.assertEqual(p.pack_tags, [])
        self.assertFalse(p.has_geotags_precomputed)
        self.assertEqual(p.num_ratings_precomputed, 0)
        self.assertEqual(p.avg_rating_precomputed, 0.0)

    def test_bulk_query_id_empty_pack_ids_returns_empty_list(self):
        # Function-entry early return; must not run any queries.
        with self.assertNumQueries(0):
            self.assertEqual(Pack.objects.bulk_query_id([]), [])

    def test_bulk_query_id_accepts_bare_int(self):
        # search/views.py + sounds/views.py call bulk_query_id(pack_id) with a bare int.
        pack = Pack.objects.create(user=self.user, name="bare-int")
        result = Pack.objects.bulk_query_id(pack.id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, pack.id)

    def test_bulk_query_id_accepts_bare_str(self):
        # A str id must be wrapped whole like any other scalar, not iterated into
        # its digit characters (which would silently query the wrong packs).
        # Explicit multi-digit id: char-splitting a single-digit id would be indistinguishable.
        pack = Pack.objects.create(id=1234, user=self.user, name="bare-str")
        result = Pack.objects.bulk_query_id(str(pack.id))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, pack.id)
