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

def task_process_sound(gearman_worker, gearman_job):
    """Run this for Gearman 'process_sound' jobs.
    """
    sound_id = gearman_job.data
    print "Processing sound with id", sound_id
    try:
        result = process(Sound.objects.select_related().get(id=sound_id))
        print "\t sound: ", sound_id, "processing", "ok" if result else "failed"
    except Sound.DoesNotExist:
        print "\t did not find sound with id: ", sound_id
        return False
    except Exception, e:
        print "\t something went terribly wrong:", e
        traceback.print_tb()
        sys.exit(255)
    return str(result)


def task_analyze_sound(gearman_worker, gearman_job):
    """Run this for Gearman essentia analysis jobs.
    """
    sound_id = gearman_job.data
    print "Analyzing sound with id", sound_id
    try:
        result = analyze(Sound.objects.get(id=sound_id))
    except Sound.DoesNotExist:
        print "\t did not find sound with id: ", sound_id
        return False
    except Exception, e:
        print "\t could not analyze sound:", e
        traceback.print_tb()
        sys.exit(255)
    return str(result)


class Command(BaseCommand):
    help = 'Run the sound processing worker'

    option_list = BaseCommand.option_list + (
        make_option('--queue', action='store', dest='queue',
            default='process_sound',
            help='Register this function (default: process_sound)'),
    )

    def handle(self, *args, **options):
        if 'task_%s' % options['queue'] not in locals():
            print "Wow.. That's crazy! Maybe try an existing queue?"
            sys.exit(1)
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        gm_worker.register_task(options['queue'], locals()[options['queue']])
        gm_worker.work()
