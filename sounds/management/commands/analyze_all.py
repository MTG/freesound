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

import json

import gearman
from django.conf import settings
from django.core.management.base import BaseCommand

from sounds.models import Sound


class Command(BaseCommand):
    help = 'Analyze all sounds that have passed moderation and have already been analyzed OK. ' \
           'This command is intended to be run  when a new Essentia extractor is deployed'

    def handle(self, *args, **options):
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        for sound in Sound.objects.filter(analysis_state='OK', moderation_state='OK'):
            # we avoid saving the sound as currently this triggers crc calculation
            # also with wait_until_complete=True we avoid processing all sounds at once in gm client machine
            gm_client.submit_job("analyze_sound", json.dumps({'sound_id': str(sound.id)}),
                                 wait_until_complete=True, background=True)
