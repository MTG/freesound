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

from django.core.management.base import BaseCommand
from sounds.models import Sound
from utils.search.search_general import add_all_sounds_to_solr, delete_sound_from_solr


class Command(BaseCommand):
    args = ''
    help = 'Take all sounds and send them to Solr'

    def handle(self, *args, **options):
        # Get all sounds moderated and processed ok
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(processing_state="OK", moderation_state="OK")
        add_all_sounds_to_solr(sound_qs, mark_index_clean=True)

        # Get all sounds that should not be in solr and remove them if they are
        sound_qs = Sound.objects.exclude(processing_state="OK", moderation_state="OK")
        for sound in sound_qs:
            delete_sound_from_solr(sound.id)  # Will only do something if sound in fact exists in solr
