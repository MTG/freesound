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

from utils.audioprocessing.freesound_audio_analysis import FreesoundAudioAnalyzer
from utils.audioprocessing.freesound_audio_processing import FreesoundAudioProcessor

workers_logger = logging.getLogger("workers")


class WorkerException(Exception):
    """
    Exception raised by the worker if:
    i) the analysis/processing function takes longer than the timeout specified in settings.WORKER_TIMEOUT
    ii) the check for free disk space  before running the analysis/processing function fails
    """
    pass


def set_timeout_alarm(time, msg):
    """
    Sets a timeout alarm which raises a WorkerException after a number of seconds.
    :param float time: seconds until WorkerException is raised
    :param str msg: message to add to WorkerException when raised
    :raises WorkerException: when timeout is reached
    """

    def alarm_handler(signum, frame):
        raise WorkerException(msg)

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(time)


def cancel_timeout_alarm():
    """
    Cancels an exsting timeout alarm (or does nothing if no alarm was set).
    """
    signal.alarm(0)


def check_if_free_space(directory=settings.PROCESSING_TEMP_DIR,
                        min_disk_space_percentage=settings.WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE):
    """
    Checks if there is free disk space in the volume of the given 'directory'. If percentage of free disk space in this
    volume is lower than 'min_disk_space_percentage', this function raises WorkerException.
    :param str directory: path of the directory whose volume will be checked for free space
    :param float min_disk_space_percentage: free disk space percentage to check against
    :raises WorkerException: if available percentage of free space is below the threshold
    """
    stats = os.statvfs(directory)
    percentage_free = stats.f_bfree * 1.0 / stats.f_blocks
    if percentage_free < min_disk_space_percentage:
        raise WorkerException("Disk is running out of space, "
                              "aborting task as there might not be enough space for temp files")


class Command(BaseCommand):
    help = 'Run the sound processing worker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue',
            action='store',
            dest='queue',
            default='process_sound',
            help='Register this function (default: process_sound)')

    def handle(self, *args, **options):
        task_name = 'task_%s' % options['queue']
        if task_name not in dir(self):
            sys.exit(1)

        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        gm_worker.register_task(options['queue'], task_func)
        workers_logger.info('Started worker with tasks: %s' % task_name)
        gm_worker.work()

    def task_analyze_sound(self, gearman_worker, gearman_job):
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        set_timeout_alarm(settings.WORKER_TIMEOUT, 'Analysis of sound %s timed out' % sound_id)

        workers_logger.info("Starting analysis of sound (%s)" % json.dumps({'sound_id': sound_id}))
        start_time = time.time()
        try:
            check_if_free_space()
            result = FreesoundAudioAnalyzer(sound_id=sound_id).analyze()
            if result:
                workers_logger.info("Finished analysis of sound (%s)" % json.dumps(
                    {'sound_id': sound_id, 'result': 'success', 'work_time': time.time() - start_time}))
            else:
                workers_logger.info("Finished analysis of sound (%s)" % json.dumps(
                    {'sound_id': sound_id, 'result': 'failure', 'work_time': time.time() - start_time}))

        except WorkerException as e:
            workers_logger.error("WorkerException while analyzing sound (%s)" % json.dumps(
                {'sound_id': sound_id, 'error': str(e), 'work_time': time.time() - start_time}))

        except Exception as e:
            workers_logger.error("Unexpected error while analyzing sound (%s)" % json.dumps(
                {'sound_id': sound_id, 'error': str(e), 'work_time': time.time() - start_time}))

        cancel_timeout_alarm()
        return ''  # Gearman requires return value to be a string

    def task_process_sound(self, gearman_worker, gearman_job):
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        skip_previews = job_data.get('skip_previews', False)
        skip_displays = job_data.get('skip_displays', False)
        set_timeout_alarm(settings.WORKER_TIMEOUT, 'Processing of sound %s timed out' % sound_id)

        workers_logger.info("Starting processing of sound (%s)" % json.dumps({'sound_id': sound_id}))
        start_time = time.time()
        try:
            check_if_free_space()
            result = FreesoundAudioProcessor(sound_id=sound_id)\
                .process(skip_displays=skip_displays, skip_previews=skip_previews)
            if result:
                workers_logger .info("Finished processing of sound (%s)" % json.dumps(
                    {'sound_id': sound_id, 'result': 'success', 'work_time': time.time() - start_time}))
            else:
                workers_logger.info("Finished processing of sound (%s)" % json.dumps(
                    {'sound_id': sound_id, 'result': 'failure', 'work_time': time.time() - start_time}))

        except WorkerException as e:
            workers_logger.error("WorkerException while processing sound (%s)" % json.dumps(
                {'sound_id': sound_id, 'error': str(e), 'work_time': time.time() - start_time}))

        except Exception as e:
            workers_logger.error("Unexpected error while processing sound (%s)" % json.dumps(
                {'sound_id': sound_id, 'error': str(e), 'work_time': time.time() - start_time}))

        cancel_timeout_alarm()
        return ''  # Gearman requires return value to be a string
