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

import logging

import gearman
import os
import sys
import traceback
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import DatabaseError
from psycopg2 import InterfaceError

from sounds.models import Sound
from utils.audioprocessing.essentia_analysis import analyze
from utils.audioprocessing.freesound_audio_processing import process

logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Run the sound processing worker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--queue',
            action='store',
            dest='queue',
            default='process_sound',
            help='Register this function (default: process_sound)')

    def write_stdout(self, msg):
        logger.info("[%d] %s" % (os.getpid(),msg))
        self.stdout.write(msg)
        self.stdout.flush()

    def handle(self, *args, **options):
        # N.B. don't take out the print statements as they're
        # very very very very very very very very very very
        # helpful in debugging supervisor+worker+gearman
        self.write_stdout('Starting worker\n')
        task_name = 'task_%s' % options['queue']
        self.write_stdout('Task: %s\n' % task_name)
        if task_name not in dir(self):
            self.write_stdout("Wow.. That's crazy! Maybe try an existing queue?\n")
            sys.exit(1)
        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        self.write_stdout('Initializing gm_worker\n')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        self.write_stdout('Registering task %s, function %s\n' % (task_name, task_func))
        gm_worker.register_task(options['queue'], task_func)
        self.write_stdout('Starting work\n')
        gm_worker.work()
        self.write_stdout('Ended work\n')

    def task_analyze_sound(self, gearman_worker, gearman_job):
        return self.task_process_x(gearman_worker, gearman_job, analyze)

    def task_process_sound(self, gearman_worker, gearman_job):
        return self.task_process_x(gearman_worker, gearman_job, process)

    def task_process_x(self, gearman_worker, gearman_job, func):
        sound_id = gearman_job.data
        self.write_stdout("Processing sound with id %s\n" % sound_id)
        sound = False
        try:
            # If the database connection has become invalid, try to reset the
            # connection (max of 'intent' times)
            intent = 3
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

            # if we didn't succeed in resetting the connection, quit the worker
            if intent <= 0:
                self.write_stdout("Problems while connecting to the database, could not reset the connection and "
                                  "will kill the worker.\n")
                sys.exit(255)

            result = func(sound)
            self.write_stdout("Finished, sound: %s, processing %s\n" % \
                              (sound_id, ("ok" if result else "failed")))
            return 'true' if result else 'false'
        except Sound.DoesNotExist:
            self.write_stdout("\t did not find sound with id: %s\n" % sound_id)
            return 'false'
        except Exception as e:
            self.write_stdout("\t something went terribly wrong: %s\n" % e)
            self.write_stdout("\t%s\n" % traceback.format_exc())
            return 'false'
