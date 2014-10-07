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
from utils.search.search_general import add_all_sounds_to_solr

class Command(BaseCommand):
    args = ''
    help = 'Add all sounds with index_dirty flag True to SOLR index'

    def handle(self, *args, **options):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(is_index_dirty=True,
                                        moderation_state='OK',
                                        processing_state='OK')

        add_all_sounds_to_solr(sound_qs, mark_index_clean=True)
