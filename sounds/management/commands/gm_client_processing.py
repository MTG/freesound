"""gm_client_processing.py

This django-admin command sends jobs to the Gearman job server, scheduling
the processing of sounds.
"""

from django.core.management.base import BaseCommand
from sounds.models import Sound
import gearman
from django.conf import settings
from optparse import make_option
from datetime import datetime


#TODO: implement queue_multisound_processing() for eficiency.

def queue_sound_processing(sound, gm_client, queue):
    """Sends a sound to the job processing queue. Logs it into django.
    """
    # Log the start of the processing.
    sound.processing_date = datetime.now()
    sound.processing_state = "PR" # processing
    sound.save()
    # Queue it.
    gm_client.submit_job(queue, str(sound.id), wait_until_complete=False,
        background=True)



class Command(BaseCommand):
    """Sends jobs to the Gearman job server, scheduling the processing
    of sounds.
    """
    help = '''Process sounds via Gearman.'''
    args = '''[<sound_id> <...>]'''

    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', dest='all', default=False,
            help='Process all sounds'),
        make_option('--pending', action='store_true', dest='pending',
            default=False, help='Process sounds marked as "pending"'),
        make_option('--queue', action='store', dest='queue',
            default='process_sound',
            help='Send job to this queue (default: process_sound)'),
    )


    def handle(self, *args, **options):
        # Parse command-line options.
        if options['all']:
            # All sounds in the database.
            sounds = Sound.objects.all().exclude(original_path=None)
        elif options['pending']:
            # Every sound marked as 'pending'.
            sounds = Sound.objects.filter(processing_state="PE"
                ).exclude(original_path=None)
        else:
            # The sound_ids passed as arguments in command-line.
            ids = [ int(arg) for arg in args ]
            sounds = Sound.objects.filter(pk__in=ids)

        # Connect to the Gearman job server.
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)

        # Queue the sounds.
        for sound in sounds:
            try:
                self.stdout.write('Posting sound to gearman "%s"\n' % sound.id)
                queue_sound_processing(sound, gm_client, options['queue'])
            except Sound.DoesNotExist:
                raise CommandError('Sound "%s" does not exist' % sound_id)
                self.stdout.write('Posting sound to gearman "%s"\n' % sound.id)
                sound = Sound.objects.get(pk=int(sound_id))


