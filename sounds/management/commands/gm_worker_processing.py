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

import errno
import json
import logging
import os
import shutil
import signal
import sys
import tempfile
import traceback

import gearman
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import DatabaseError
from psycopg2 import InterfaceError

from sounds.models import Sound
from utils.audioprocessing.freesound_audio_analysis import analyze
from utils.audioprocessing.freesound_audio_processing import process

logger = logging.getLogger("console")


class WorkerException(Exception):
    pass


def set_timeout_alarm(time, msg):

    def alarm_handler(signum, frame):
        raise WorkerException(msg)

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(time)


def cancel_timeout_alarm():
    signal.alarm(0)


def log(msg):
    logger.info("[%d] %s" % (os.getpid(), msg))


def log_error(msg):
    log('ERROR: %s' % msg)


def cleanup_tmp_directory(tmp_directory):
    if tmp_directory is not None:
        try:
            shutil.rmtree(tmp_directory)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Directory does not exist, do nothing about it
            else:
                log_error("Could not clean tmp files in %s: %s" % (tmp_directory, e))
        except Exception as e:
            log_error("Could not clean tmp files in %s: %s" % (tmp_directory, e))


def check_if_free_space(directory='/tmp/', min_disk_space_percentage=0.05):
    """
    Raises a WorkerException if the perfectage of free disk space in the volume of the given 'directory' is lower
    than 'min_disk_space_percentage'.
    """
    stats = os.statvfs(directory)
    percetage_free = stats.f_bfree * 1.0 / stats.f_blocks
    if percetage_free < min_disk_space_percentage:
        raise WorkerException("Disk is running out of space, "
                              "aborting task as there might not be enough space for temp files")


def get_sound_object(sound_id):
    # Get the Sound object from DB
    # TODO: is all this really needed?
    sound = None
    intent = 3
    try:
        # If the database connection has become invalid, try to reset the
        # connection (max of 'intent' times)
        while intent > 0:
            try:
                # Try to get the sound, and if we succeed continue as normal
                sound = Sound.objects.get(id=sound_id)
                break
            except (InterfaceError, DatabaseError):
                # Try to close the current connection (it probably already is closed)
                try:
                    connection.connection.close()
                except:
                    pass
                # Trick Django into creating a fresh connection on the next db use attempt
                connection.connection = None
                intent -= 1

    except Sound.DoesNotExist:
        raise WorkerException("Did not find sound with id: %s" % sound_id)

    except Exception as e:
        raise WorkerException("Unexpected error while getting sound from DB: %s\n\t%s"
                              % (e, traceback.format_exc()))

    # if we didn't succeed in resetting the connection, quit the worker
    if intent <= 0:
        raise WorkerException("Problems while connecting to the database, could not reset the connection and "
                              "will kill the worker.")

    return sound


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
        log('Starting worker')
        task_name = 'task_%s' % options['queue']
        log('Task: %s' % task_name)
        if task_name not in dir(self):
            log("Wow.. That's crazy! Maybe try an existing queue?")
            sys.exit(1)

        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        log('Initializing gm_worker')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        log('Registering task %s, function %s' % (task_name, task_func))
        gm_worker.register_task(options['queue'], task_func)
        log('Starting work')
        gm_worker.work()
        log('Ended work')

    def task_analyze_sound(self, gearman_worker, gearman_job):
        tmp_directory = None
        job_data = json.loads(gearman_job.data)
        sound_id = job_data['sound_id']
        set_timeout_alarm(settings.WORKER_TIMEOUT, 'Analysis of sound %s timed out' % sound_id)

        log("---- Starting analysis of sound with id %s ----" % sound_id)
        try:
            check_if_free_space()
            tmp_directory = tempfile.mkdtemp(prefix='analysis_%s_' % sound_id)
            sound = get_sound_object(sound_id)
            result = analyze(sound)
            log("Finished analysis of sound with id %s: %s" % (sound_id, ("OK" if result else "FALIED")))

        except WorkerException as e:
            log_error(e)

        except Exception as e:
            log_error('Unexpected error while analyzing sound: %s' % e)

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

        log("---- Starting processing of sound with id %s ----" % sound_id)
        try:
            check_if_free_space()
            tmp_directory = tempfile.mkdtemp(prefix='processing_%s_' % sound_id)
            sound = get_sound_object(sound_id)
            result = process(
                sound, skip_displays=skip_displays, skip_previews=skip_previews, tmp_directory=tmp_directory)
            log("Finished processing of sound with id %s: %s" % (sound_id, ("OK" if result else "FALIED")))

        except WorkerException as e:
            log_error(e)

        except Exception as e:
            log_error('Unexpected error while processing sound: %s' % e)

        cancel_timeout_alarm()
        cleanup_tmp_directory(tmp_directory)
        return ''  # Gearman requires return value to be a string
