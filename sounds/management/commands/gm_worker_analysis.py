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
        analyzer = job_data.get('analyzer', False)

        workers_logger.info("Starting analysis (v2) of sound (%s)" % json.dumps(
            {'task_name': task_name, 'sound_id': sound_id, 'analyzer':analyzer}))

        try:
            check_if_free_space()
            sound = Sound.objects.get(id=sound_id)
            # Analysis happens here, this one is a fake one
            result = json.dumps({'loudness':40, 'spectral_centroid':1500})
            # Handle analysis failure commented for the future
            # if result:
            SoundAnalysis.objects.get_or_create(sound=sound, analyzer=analyzer,
                                            analyzer_version=1,
                                            analysis_data=result)
            sound.set_analysis_state("OK")
            workers_logger.info("Analysis finished (%s)" % json.dumps(
                 {'task_name': task_name, 'sound_id': sound_id, 'analyzer':analyzer}))
            # else:
            #     workers_logger.info("Finished analysis of sound (%s)" % json.dumps(
            #         {'task_name': task_name, 'sound_id': sound_id, 'result': 'failure',
            #          'work_time': round(time.time() - start_time)}))

        except Sound.DoesNotExist as e:
            workers_logger.error("Failed to analyze a sound that does not exist (%s)"% json.dumps(
                {'task_name': task_name, 'sound_id': sound_id, 'analyzer':analyzer, 'error': str(e)}))
        except WorkerException as e:
            workers_logger.error("WorkerException while analyzing sound (%s)" % json.dumps(
                {'task_name': task_name, 'sound_id': sound_id, 'analyzer':analyzer, 'error': str(e),
                 'work_time': round(time.time() - start_time)}))

        except Exception as e:
            workers_logger.error("Unexpected error while analyzing sound (%s)" % json.dumps(
                {'task_name': task_name, 'sound_id': sound_id, 'analyzer':analyzer, 'error': str(e),
                 'work_time': round(time.time() - start_time)}))

        cancel_timeout_alarm()
        return ''  # Gearman requires return value to be a string