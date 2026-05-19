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


import pytest
from django.core.management import call_command

from sounds.models import RemixGroup, Sound
from utils.test_helpers import create_user_and_sounds


@pytest.mark.django_db
class TestCreateRemixGroups:
    @pytest.fixture(autouse=True)
    def _fixtures(self):
        call_command("loaddata", "licenses", "email_preference_type")

    def test_idempotent_run_does_not_dirty_sounds(self):
        # Build a single component {A,B,C,D} via three edges
        _, _, sounds = create_user_and_sounds(num_sounds=4, username="remixuser1")
        a, b, c, d = sounds
        a.change_sources_and_propagate({b.id})  # A -> B
        b.change_sources_and_propagate({c.id})  # B -> C
        d.change_sources_and_propagate({a.id})  # D -> A

        call_command("create_remix_groups")
        # Reset is_index_dirty introduced by change_sources_and_propagate / first cron run
        Sound.objects.filter(id__in=[a.id, b.id, c.id, d.id]).update(is_index_dirty=False)

        # Second cron run on identical graph must not re-dirty any sound
        call_command("create_remix_groups")
        assert Sound.objects.filter(id__in=[a.id, b.id, c.id, d.id], is_index_dirty=True).count() == 0

        # Group structure preserved
        assert RemixGroup.objects.count() == 1
        rg = RemixGroup.objects.first()
        assert rg is not None
        assert set(rg.sounds.values_list("id", flat=True)) == {a.id, b.id, c.id, d.id}

    def test_change_sources_marks_counterparties_dirty(self):
        _, _, sounds = create_user_and_sounds(num_sounds=2, username="remixuser2")
        a, b = sounds

        # Adding B as a source of A flips B.was_remixed False -> True
        Sound.objects.filter(id__in=[a.id, b.id]).update(is_index_dirty=False)
        a.change_sources_and_propagate({b.id})
        b.refresh_from_db()
        assert b.is_index_dirty is True

        # Removing B as a source of A flips B.was_remixed True -> False
        Sound.objects.filter(id__in=[a.id, b.id]).update(is_index_dirty=False)
        a.change_sources_and_propagate(set())
        b.refresh_from_db()
        assert b.is_index_dirty is True

    def test_sound_deletion_marks_counterparties_dirty(self):
        _, _, sounds = create_user_and_sounds(num_sounds=2, username="remixuser3")
        a, b = sounds
        a.change_sources_and_propagate({b.id})

        Sound.objects.filter(id__in=[a.id, b.id]).update(is_index_dirty=False)
        a.delete()
        b.refresh_from_db()
        assert b.is_index_dirty is True
