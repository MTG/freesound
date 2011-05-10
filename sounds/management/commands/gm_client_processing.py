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
from django.db import transaction

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
        make_option('--file', action='store', dest='file_input',
            default=None,
            help='Take ids from a file instead of via commands'),
    )


    def handle(self, *args, **options):
        # Parse command-line options.
        qs = Sound.objects.select_related()

        if options['all']:
            # All sounds in the database.
            sounds = qs.all().exclude(original_path=None)
        elif options['pending']:
            # Every sound marked as 'pending'.
            sounds = qs.filter(processing_state="PE").exclude(original_path=None)
        else:
            # The sound_ids passed as arguments in command-line.
            sounds = qs.filter(pk__in=args).exclude(original_path=None)

        # update all sounds to reflect we are processing them...
        self.stdout.write('Updating database\n')
        sounds.update(processing_date=datetime.now(), processing_state="PR")
        transaction.commit_unless_managed()
        self.stdout.write('Updating database done\n')

        # Connect to the Gearman job server.
        gearman_task = options['queue']
        jobs = [{'task': gearman_task, 'data': str(sound["id"])} for sound in sounds.values("id")]

        self.stdout.write('Sending %d sound(s) to the gearman queue\n' % len(jobs))
        # send them to the queue!
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        gm_client.submit_multiple_jobs(jobs, background=True, wait_until_complete=False)
        self.stdout.write('Sending sounds done')
