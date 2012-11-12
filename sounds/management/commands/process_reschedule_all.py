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

from django.core.management.base import NoArgsCommand
from sounds.models import Sound
from django.db.models import Q

class Command(NoArgsCommand):
    args = '<num_days>'
    help = 'Take all sounds that are sitting the processing queue marked as "queue" and reschedule them'

    def handle(self, **options):
        Sound.objects.filter(Q(processing_state='PR') | Q(processing_state='QU')).update(processing_state = "PE")
