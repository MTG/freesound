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

import gearman
from django.core.management.base import BaseCommand
from django.conf import settings
from sounds.models import Sound, RandomSound


class Command(BaseCommand):

    help = 'Add new RandomSound'

    def handle(self, *args, **options):
        print 'Create new RandomSound task'
        random_sound_id = Sound.objects.random()
        sound = Sound.objects.get(id=random_sound_id)
        rnd = RandomSound.objects.create(sound=sound)
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        gm_client.submit_job("email_random_sound", str(rnd.id),
                wait_until_complete=False, background=True)
        print "Create new RandomSound task ended"


