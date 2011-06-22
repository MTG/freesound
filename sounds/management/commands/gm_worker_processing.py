"""gm_worker_processing.py

This django-admin command runs a Gearman worker for processing sounds.
"""

import gearman, sys
from django.core.management.base import BaseCommand
from utils.audioprocessing.freesound_audio_processing import process
from utils.audioprocessing.essentia_analysis import analyze
from django.conf import settings
from sounds.models import Sound
from optparse import make_option
import traceback

# TODO: DRY-out!







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
        self.stdout.write('Starting worker\n')
        task_name = 'task_%s' % options['queue']
        self.stdout.write('Task: %s\n' % task_name)
        if task_name not in dir(self):
            self.stdout.write("Wow.. That's crazy! Maybe try an existing queue?\n")
            sys.exit(1)
        task_func = getattr(Command, task_name)
        self.stdout.write('Initializing gm_worker\n')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        self.stdout.write('Registering task %s, function %s\n' % (task_name, task_func))
        gm_worker.register_task(options['queue'], task_func)
        self.stdout.write('Starting work\n')
        gm_worker.work()
        self.stdout.write('Ended work\n')

    def task_analyze_sound(self, gearman_worker, gearman_job):
        """Run this for Gearman essentia analysis jobs.
        """
        sound_id = gearman_job.data
        self.stdout.write("Analyzing sound with id %s\n" % sound_id)
        try:
            result = analyze(Sound.objects.get(id=sound_id))
        except Sound.DoesNotExist:
            self.stdout.write("\t did not find sound with id: %s\n" % sound_id)
            return False
        except Exception, e:
            self.stdout.write("\t could not analyze sound: %s\n" % e)
            self.stdout.write("\t%s\n" % traceback.format_tb())
            sys.exit(255)
        return str(result)

    def task_process_sound(self, gearman_worker, gearman_job):
        """Run this for Gearman 'process_sound' jobs.
        """
        sound_id = gearman_job.data
        self.stdout.write("Processing sound with id %s\n" % sound_id)
        try:
            result = process(Sound.objects.select_related().get(id=sound_id))
            self.stdout.write("\t sound: %s, processing %s\n" % \
                              (sound_id, ("ok" if result else "failed")))
        except Sound.DoesNotExist:
            self.stdout.write("\t did not find sound with id: %s\n" % sound_id)
            return False
        except Exception, e:
            self.stdout.write("\t something went terribly wrong: %s\n" % e)
            traceback.print_tb()
            sys.exit(255)
        return str(result)
