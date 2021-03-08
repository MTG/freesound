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
import logging
import os
import signal
import sys
import time

import gearman
from django.conf import settings
from django.core.management.base import BaseCommand

from sounds.models import Sound, SoundAnalysis

workers_logger = logging.getLogger("workers")


class Command(BaseCommand):
    help = 'Run the sound analysis worker v2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue',
            action='store',
            dest='queue',
            default='analyze_sound_v2',
            help='Register this function (default: analyze_sound_v2)')

    def handle(self, *args, **options):
        task_name = 'task_%s' % options['queue']
        if task_name not in dir(self):
            sys.exit(1)

        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        gm_worker.register_task(options['queue'], task_func)
        workers_logger.info('Started worker with tasks: %s' % task_name)
        gm_worker.work()

    def task_analyze_sound_v2(self, gearman_worker, gearman_job):
        task_name = 'analyze_sound_v2'
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        extractor = job_data.get('extractor', False)

        workers_logger.info("Starting fake analysis of sound (%s)" % json.dumps(
            {'task_name': task_name, 'sound_id': sound_id, 'extractor':extractor}))

        sound = Sound.objects.get(id=sound_id)
        fake_analysis_data = json.dumps({'loudness':40, 'spectral_centroid':1500})
        SoundAnalysis.objects.get_or_create(sound=sound, extractor=extractor,
                                            extractor_version="hello",
                                            analysis_data=fake_analysis_data)

        workers_logger.info("Analysis finished (%s)" % json.dumps(
            {'task_name': task_name, 'sound_id': sound_id, 'extractor':extractor}))
        return ''  # Gearman requires return value to be a string