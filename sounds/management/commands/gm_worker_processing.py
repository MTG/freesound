"""gm_worker_processing.py

This django-admin command runs a Gearman worker for processing sounds.
"""

import gearman, sys, traceback, json, time
from django.core.management.base import BaseCommand
from utils.audioprocessing.freesound_audio_processing import process
from utils.audioprocessing.essentia_analysis import analyze
from django.conf import settings
from sounds.models import Sound, Pack
from optparse import make_option
from psycopg2 import InterfaceError
from django.db.utils import DatabaseError
from django.db import connection
import logging

logger = logging.getLogger("processing")

class Command(BaseCommand):
    help = 'Run the sound processing worker'

    option_list = BaseCommand.option_list + (
        make_option('--queue', action='store', dest='queue',
            default='process_sound',
            help='Register this function (default: process_sound)'),
    )

    def handle(self, *args, **options):
        # N.B. don't take out the print statements as they're
        # very very very very very very very very very very
        # helpful in debugging supervisor+worker+gearman
        logger.info('Starting worker')
        
        task_name = 'task_%s' % options['queue']
        logger.info('Task: %s\n' % task_name)
        if task_name not in dir(self):
            logger.warning("Wow.. That's crazy! Maybe try an existing queue?")
            sys.exit(1)
        task_func = lambda x, y: getattr(Command, task_name)(self, x, y)
        
        logger.info('Initializing gm_worker')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        
        logger.info('Registering task %s, function %s\n' % (task_name, task_func))
        gm_worker.register_task(options['queue'], task_func)
        
        logger.info('Starting work')
        gm_worker.work()
        logger.info('Ended work')


    def task_analyze_sound(self, gearman_worker, gearman_job):
        return self.task_process_x(gearman_worker, gearman_job, analyze)


    def task_process_sound(self, gearman_worker, gearman_job):
        return self.task_process_x(gearman_worker, gearman_job, process)

    def task_create_pack_zip(self, gearmanworker, gearman_job):
        # dirty hack: sleep 1 sec while the transaction finishes at the other end
        time.sleep(1)
        pack_id  = gearman_job.data
        self.write_stdout("Processing pack with id %s\n" % pack_id)
        pack = Pack.objects.get(id=int(pack_id))
        self.write_stdout("Found pack with id %d\n" % pack.id)
        pack.create_zip()
        self.write_stdout("Finished creating zip")
        return 'true'
    
    def task_process_x(self, gearman_worker, gearman_job, func):
        sound_id = gearman_job.data
        logger.info("Processing sound with id %s\n" % sound_id)
        success = True
        sound = False
        try:
            # If the database connection has become invalid, try to reset the
            # connection (max of 'intent' times)
            intent = 3
            while intent > 0:
                try:
                    # Try to get the sound, and if we succeed continue as normal
                    sound = Sound.objects.select_related().get(id=sound_id)
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
                logger.info("Problems while connecting to the database, could not reset the connection and will kill the worker.\n")
                sys.exit(255)

            result = func(sound)
            logger.info("Finished, sound: %s, processing %s\n" % \
                              (sound_id, ("ok" if result else "failed")))
            success = result
            return 'true' if result else 'false'
        except Sound.DoesNotExist:
            logger.warning("\t did not find sound with id: %s\n" % sound_id)
            success = False
            return 'false'
        except (DatabaseError, InterfaceError):
            logger.error("Problems while connecting to the database, will kill the worker.")
            sys.exit(255)
        except Exception, e:
            logger.info("\t something went terribly wrong: %s\n" % e)
            logger.info("\t%s\n" % traceback.format_exc())
            success = False
            return 'false'
