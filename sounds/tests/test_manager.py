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

import datetime

import pytest
from django.conf import settings
from django.test import TestCase

from geotags.models import GeoTag
from sounds.models import License, Pack, Sound
from tickets.models import Ticket
from utils.test_helpers import (
    create_consolidated_audio_descriptors_and_similarity_vectors_for_sound,
    create_user_and_sounds,
)


def create_representative_pack(username, count_offset, geotag_date, *, start_date=datetime.date(2024, 1, 1)):
    cc0 = License.objects.get(abbreviation="cc0")
    attribution = License.objects.get(abbreviation="by")
    unpublished_license = License.objects.get(abbreviation="samp+")
    created = datetime.datetime.combine(start_date, datetime.time(), tzinfo=datetime.timezone.utc)
    _, packs, sounds = create_user_and_sounds(
        num_sounds=5,
        num_packs=1,
        username=username,
        count_offset=count_offset,
        processing_state="OK",
        moderation_state="OK",
    )
    pack = packs[0]
    oldest, middle, newer, newest, unpublished = sounds
    for day, sound in enumerate(sounds):
        sound.created = created + datetime.timedelta(days=day)
        sound.duration = day + 0.5
        sound.license = cc0
        sound.save()
        sound.set_tags([username])

    oldest.license = attribution
    oldest.num_ratings = settings.MIN_NUMBER_RATINGS
    oldest.avg_rating = 6.0
    oldest.save()
    oldest.set_tags([username, "old-only"])
    middle.num_ratings = settings.MIN_NUMBER_RATINGS + 1
    middle.avg_rating = 8.0
    middle.save()
    newer.num_ratings = settings.MIN_NUMBER_RATINGS - 1
    newer.avg_rating = 10.0
    newer.save()
    unpublished.processing_state = "PE"
    unpublished.license = unpublished_license
    unpublished.num_ratings = settings.MIN_NUMBER_RATINGS
    unpublished.avg_rating = 10.0
    unpublished.save()
    unpublished.set_tags(["unpublished-only"])
    create_consolidated_audio_descriptors_and_similarity_vectors_for_sound(newest)
    GeoTag.objects.create(sound=pack.sounds.get(created__date=geotag_date), lat=1.0, lon=1.0, zoom=1)
    pack.process()
    return pack


@pytest.fixture
def licenses(load_fixtures):
    load_fixtures(["licenses"])


@pytest.fixture
def populated_pack(licenses):
    """Public sounds dated January 1–4; an unpublished sound dated January 5."""
    return create_representative_pack("field_recordist", 0, datetime.date(2024, 1, 1))


@pytest.fixture
def other_populated_pack(licenses):
    """February sounds, all public sounds CC0, with one rated sound and an unpublished geotag."""
    pack = create_representative_pack(
        "synth_player", 100, datetime.date(2024, 2, 5), start_date=datetime.date(2024, 2, 1)
    )
    oldest = pack.sounds.get(created__date=datetime.date(2024, 2, 1))
    oldest.license = License.objects.get(abbreviation="cc0")
    oldest.num_ratings = 0
    oldest.save()
    oldest.set_tags(["synth_player", "tone"])
    newest = pack.sounds.get(created__date=datetime.date(2024, 2, 4))
    newest.set_tags(["synth_player", "tone"])
    return pack


def expected_pack_player(sound, *, ready=False):
    return {
        "id": sound.id,
        "username": sound.user.username,
        "ready_for_similarity": ready,
        "duration": sound.duration,
        "preview_mp3": sound.locations("preview.LQ.mp3.url"),
        "preview_ogg": sound.locations("preview.LQ.ogg.url"),
        "wave": sound.locations("display.wave.L.url"),
        "spectral": sound.locations("display.spectral.L.url"),
        "num_ratings": sound.num_ratings,
        "avg_rating": sound.avg_rating,
    }


def test_pack_selects_newest_public_sounds(populated_pack, other_populated_pack):
    # returns the three newest sounds for each pack
    results = Pack.objects.dict_ids([populated_pack.id, other_populated_pack.id])

    first_pack = results[populated_pack.id]
    first_pack_sound_dates = [
        first_pack.sounds.get(id=sound_data["id"]).created.date() for sound_data in first_pack.selected_sounds_data
    ]
    assert first_pack_sound_dates == [
        datetime.date(2024, 1, 4),
        datetime.date(2024, 1, 3),
        datetime.date(2024, 1, 2),
    ]

    second_pack = results[other_populated_pack.id]
    second_pack_sound_dates = [
        second_pack.sounds.get(id=sound_data["id"]).created.date() for sound_data in second_pack.selected_sounds_data
    ]
    assert second_pack_sound_dates == [
        datetime.date(2024, 2, 4),
        datetime.date(2024, 2, 3),
        datetime.date(2024, 2, 2),
    ]


def test_pack_selects_requested_sounds(populated_pack, other_populated_pack):
    # bulk_query_id if you ask for data for specific sounds in the pack
    requested = populated_pack.sounds.get(created__date=datetime.date(2024, 1, 1))
    unpublished = populated_pack.sounds.get(created__date=datetime.date(2024, 1, 5))
    other_sound = other_populated_pack.sounds.get(created__date=datetime.date(2024, 2, 4))
    selection = {
        populated_pack.id: [requested.id, unpublished.id, other_sound.id],
        other_populated_pack.id: [other_sound.id],
    }
    results = {}
    for pack in Pack.objects.bulk_query_id([populated_pack.id, other_populated_pack.id], selection):
        results[pack.id] = pack

    assert results[populated_pack.id].selected_sounds_data == [expected_pack_player(requested)]
    assert results[other_populated_pack.id].selected_sounds_data == [expected_pack_player(other_sound, ready=True)]


def test_pack_aggregate_data_uses_all_public_sounds(populated_pack, other_populated_pack):
    # lists of licenses, tags, ratings and geotags is based on all public sounds in a pack
    cc0 = License.objects.get(abbreviation="cc0")
    attribution = License.objects.get(abbreviation="by")
    results = Pack.objects.dict_ids([populated_pack.id, other_populated_pack.id])
    first_pack = results[populated_pack.id]
    assert first_pack.num_sounds_unpublished_precomputed == 1
    assert first_pack.licenses_data_precomputed == [
        {"id": cc0.id, "name": cc0.name},
        {"id": attribution.id, "name": attribution.name},
    ]
    assert first_pack.license_summary_name_and_id == ("Various licenses", None)
    assert first_pack.pack_tags == [
        {"name": "field_recordist", "count": 4, "browse_url": first_pack.browse_pack_tag_url("field_recordist")},
        {"name": "old-only", "count": 1, "browse_url": first_pack.browse_pack_tag_url("old-only")},
    ]
    assert first_pack.num_ratings_precomputed == 2
    assert first_pack.avg_rating_precomputed == pytest.approx(7.0)
    assert first_pack.user_profile_locations == populated_pack.user.profile.locations()
    assert first_pack.has_geotags_precomputed is True

    second_pack = results[other_populated_pack.id]
    assert second_pack.num_sounds_unpublished_precomputed == 1
    assert second_pack.licenses_data_precomputed == [{"id": cc0.id, "name": cc0.name}]
    assert second_pack.license_summary_name_and_id == (cc0.name, cc0.id)
    assert second_pack.pack_tags == [
        {"name": "synth_player", "count": 4, "browse_url": second_pack.browse_pack_tag_url("synth_player")},
        {"name": "tone", "count": 2, "browse_url": second_pack.browse_pack_tag_url("tone")},
    ]
    assert second_pack.num_ratings_precomputed == 1
    assert second_pack.avg_rating_precomputed == pytest.approx(8.0)
    assert second_pack.user_profile_locations == other_populated_pack.user.profile.locations()
    assert second_pack.has_geotags_precomputed is False


def test_pack_query_count(populated_pack, other_populated_pack, django_assert_num_queries):
    # No more than 4 queries to get the data for any number of packs
    with django_assert_num_queries(4):
        assert len(Pack.objects.bulk_query_id([populated_pack.id, other_populated_pack.id])) == 2


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

    def test_ordered_ids_num_queries(self):
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

    def test_ordered_ids_field_contents(self):
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
        # No fixture sounds are public, so no similarity lookup runs.
        # Expect three queries: packs, selected sounds, and tags.
        self.assertEqual(Sound.public.filter(pack_id__in=self.pack_ids).count(), 0)
        with self.assertNumQueries(3):
            pack_ids_with_duplicates = self.pack_ids + self.pack_ids
            for i, pack in enumerate(Pack.objects.ordered_ids(pack_ids=pack_ids_with_duplicates)):
                self.assertEqual(type(pack), Pack)
                self.assertEqual(pack_ids_with_duplicates[i], pack.id)

    def test_ordered_ids_queryset(self):
        pack_ids = Pack.objects.filter(id__in=self.pack_ids).order_by("-id").values_list("id", flat=True)
        self.assertEqual([pack.id for pack in Pack.objects.ordered_ids(pack_ids)], sorted(self.pack_ids, reverse=True))

    def test_pack_lookup_missing_and_deleted(self):
        pack = Pack.objects.create(user=self.user, name="deleted lookup", is_deleted=True)
        missing_id = Pack.objects.order_by("-id").values_list("id", flat=True).first() + 1
        pack_ids = [pack.id, missing_id, pack.id]
        self.assertEqual(Pack.objects.dict_ids(pack_ids), {})
        self.assertEqual(Pack.objects.ordered_ids(pack_ids), [])
        self.assertEqual(list(Pack.objects.dict_ids(pack_ids, exclude_deleted=False)), [pack.id])
        self.assertEqual([p.id for p in Pack.objects.ordered_ids(pack_ids, exclude_deleted=False)], [pack.id, pack.id])

    def test_bulk_query_id_sound_ids_for_pack_id_missing_raises(self):
        pack_a = Pack.objects.create(user=self.user, name="A")
        pack_b = Pack.objects.create(user=self.user, name="B")
        sound = self._make_sound(self.user, pack_a, "preselect-a")
        with self.assertRaises(ValueError):
            Pack.objects.bulk_query_id(
                [pack_a.id, pack_b.id],
                sound_ids_for_pack_id={pack_a.id: [sound.id]},
            )

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
        Sound.objects.filter(id=s_mid_a.id).update(created=s_mid_b.created)
        s_mid_a.refresh_from_db()

        p = Pack.objects.bulk_query_id([pack.id])[0]
        top_ids = [d["id"] for d in p.selected_sounds_data]
        # `created` ranking: s_new (latest) > {s_mid_a, s_mid_b} (tie) > s_old.
        # Tiebreaker -id puts higher id first among ties.
        higher_mid, lower_mid = sorted([s_mid_a.id, s_mid_b.id], reverse=True)
        self.assertEqual(top_ids, [s_new.id, higher_mid, lower_mid])

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

    def test_bulk_query_id_empty_pack_ids_returns_empty_list(self):
        with self.assertNumQueries(0):
            self.assertEqual(Pack.objects.bulk_query_id([]), [])

    def test_bulk_query_id_empty_pack(self):
        pack = Pack.objects.create(user=self.user, name="empty")
        result = Pack.objects.bulk_query_id([pack.id])[0]
        self.assertEqual(result.selected_sounds_data, [])
        self.assertEqual(result.num_sounds_unpublished_precomputed, 0)
        self.assertEqual(result.licenses_data_precomputed, [])
        self.assertEqual(result.license_summary_name_and_id, ("Various licenses", None))
        self.assertEqual(result.pack_tags, [])
        self.assertFalse(result.has_geotags_precomputed)
        self.assertEqual(result.num_ratings_precomputed, 0)
        self.assertEqual(result.avg_rating_precomputed, 0.0)

    def test_bulk_query_id_accepts_bare_int(self):
        pack = Pack.objects.create(user=self.user, name="bare-int")
        result = Pack.objects.bulk_query_id(pack.id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, pack.id)

    def test_bulk_query_id_accepts_bare_str(self):
        # Use a multi-digit ID to detect accidental character splitting.
        pack = Pack.objects.create(id=1234, user=self.user, name="bare-str")
        result = Pack.objects.bulk_query_id(str(pack.id))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, pack.id)
