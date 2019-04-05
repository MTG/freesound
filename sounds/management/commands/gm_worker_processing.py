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
import tempfile

import gearman
from django.conf import settings
from django.core.management.base import BaseCommand

from utils.audioprocessing.freesound_audio_analysis import FreesoundAudioAnalyzer
from utils.audioprocessing.freesound_audio_processing import FreesoundAudioProcessor
from utils.filesystem import remove_directory

logger = logging.getLogger("processing")
logger_error = logging.getLogger("processing_errors")


class WorkerException(Exception):
    pass


def set_timeout_alarm(time, msg):

    def alarm_handler(signum, frame):
        raise WorkerException(msg)

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(time)


def cancel_timeout_alarm():
    signal.alarm(0)


def cleanup_tmp_directory(tmp_directory):
    if tmp_directory is not None:
        try:
            remove_directory(tmp_directory)
        except Exception as e:
            log_error("Could not clean tmp files in %s: %s" % (tmp_directory, e))


def log_error(message):
    logger.error(message)
    logger_error.info(message)


def check_if_free_space(directory='/tmp/', min_disk_space_percentage=0.05):
    """
    Raises an Exception if the perfectage of free disk space in the volume of the given 'directory' is lower
    than 'min_disk_space_percentage'.
    """
    stats = os.statvfs(directory)
    percetage_free = stats.f_bfree * 1.0 / stats.f_blocks
    if percetage_free < min_disk_space_percentage:
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
        logger.info('Starting worker')
        task_name = 'task_%s' % options['queue']
        logger.info('Task: %s' % task_name)
        if task_name not in dir(self):
            logger.info("Wow.. That's crazy! Maybe try an existing queue?")
            sys.exit(1)

        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        logger.info('Initializing gm_worker')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        logger.info('Registering task %s, function %s' % (task_name, task_func))
        gm_worker.register_task(options['queue'], task_func)
        logger.info('Starting work')
        gm_worker.work()
        logger.info('Ended work')

    def task_analyze_sound(self, gearman_worker, gearman_job):
        tmp_directory = None
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        set_timeout_alarm(settings.WORKER_TIMEOUT, 'Analysis of sound %s timed out' % sound_id)

        logger.info("---- Starting analysis of sound with id %s ----" % sound_id)
        try:
            check_if_free_space()
            tmp_directory = tempfile.mkdtemp(prefix='analysis_%s_' % sound_id)
            result = FreesoundAudioAnalyzer(sound_id=sound_id, tmp_directory=tmp_directory).analyze()
            if result:
                logger.info("Successfully analyzed sound %s" % sound_id)
            else:
                log_error("Failed analyizing sound %s" % sound_id)

        except WorkerException as e:
            log_error('%s' % e)

        except Exception as e:
            log_error('Unexpected error while analyzing sound %s' % e)

        cancel_timeout_alarm()
        cleanup_tmp_directory(tmp_directory)
        return ''  # Gearman requires return value to be a string

    def task_process_sound(self, gearman_worker, gearman_job):
        tmp_directory = None
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        skip_previews = job_data.get('skip_previews', False)
        skip_displays = job_data.get('skip_displays', False)
        set_timeout_alarm(settings.WORKER_TIMEOUT, 'Processing of sound %s timed out' % sound_id)

        logger.info("---- Starting processing of sound with id %s ----" % sound_id)
        try:
            check_if_free_space()
            tmp_directory = tempfile.mkdtemp(prefix='processing_%s_' % sound_id)
            result = FreesoundAudioProcessor(sound_id=sound_id, tmp_directory=tmp_directory)\
                .process(skip_displays=skip_displays, skip_previews=skip_previews)
            if result:
                logger.info("Successfully processed sound %s" % sound_id)
            else:
                log_error("Failed processing sound %s" % sound_id)

        except WorkerException as e:
            log_error('%s' % e)

        except Exception as e:
            log_error('Unexpected error while processing sound %s' % e)

        cancel_timeout_alarm()
        cleanup_tmp_directory(tmp_directory)
        return ''  # Gearman requires return value to be a string
