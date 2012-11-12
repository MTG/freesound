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
from datetime import datetime
from django.db.models import Q

class Command(BaseCommand):
    args = '<num_hours>'
    help = 'Take all sounds that have been sitting (for num_hours) the processing queue marked as "being processed" and reschedule them'

    def handle(self, *args, **options):
        num_hours = int(args[0])
        for sound in Sound.objects.filter(Q(processing_state='PR') | Q(processing_state='QU'), processing_date__lt=datetime.now()-datetime.timedelta(hours=num_hours)):
            sound.processing_state = "PE"
            sound.save()
