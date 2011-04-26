"""gm_worker_processing.py

This django-admin command runs a Gearman worker for processing sounds.
"""

import gearman
from django.core.management.base import BaseCommand
from utils.audioprocessing.freesound_audio_processing import process
from django.conf import settings
from sounds.models import Sound
from optparse import make_option
import sys

def task_process_sound(gearman_worker, gearman_job):
    """Run this for Gearman 'process_sound' jobs.
    """
    sound_id = gearman_job.data
    print "Processing sound with id", sound_id
    try:
        result = process(Sound.objects.select_related().get(id=sound_id))
        print "\tsound: ", sound_id, "processing", "ok" if result else "failed"
    except Sound.DoesNotExist:
        print "\tdid not find sound with id: ", sound_id
        return False
    except Exception, e:
        print "\t something went terribly wrong:", e
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
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        gm_worker.register_task(options['queue'], task_process_sound)
        gm_worker.work()
