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

from django.core.management.base import BaseCommand
from sounds.models import Sound
import gearman, sys
from django.conf import settings
from optparse import make_option
from datetime import datetime
from django.db import transaction

VALID_QUEUES = ['process_sound', 'analyze_sound']

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
            default=None,
            help='Send job to this queue (default: process_sound)'),
        make_option('--file', action='store', dest='file_input',
            default=None,
            help='Take ids from a file instead of via commands'),
    )


    def handle(self, *args, **options):
        # Parse command-line options.
        qs = Sound.objects.select_related()

        gearman_task = options['queue']
        if gearman_task not in VALID_QUEUES:
            print "Wow.. You're mad as a hatter! Are you sure that's the queue you want? Pick one from: %s." % ', '.join(VALID_QUEUES)
            sys.exit(1)

        if options['all']:
            # All sounds in the database.
            sounds = qs.all().exclude(original_path=None)
        elif options['pending']:
            # Every sound marked as 'pending'.
            if gearman_task == 'process_sound':
                sounds = qs.filter(processing_state="PE").exclude(original_path=None)
            elif gearman_task == 'analyze_sound':
                sounds = qs.filter(analysis_state="PE").exclude(original_path=None)
        else:
            # The sound_ids passed as arguments in command-line.
            sounds = qs.filter(pk__in=args).exclude(original_path=None)

        # generate the job list before the queryset gets updated.
        jobs = [{'task': gearman_task, 'data': str(sound["id"])} for sound in sounds.values("id")]

        # update all sounds to reflect we are processing them... (only for 'process_sound' queue)
        self.stdout.write('Updating database\n')
        if gearman_task == 'process_sound':
            sounds.update(processing_date=datetime.now(), processing_state="QU")
            transaction.commit_unless_managed()
        elif gearman_task == 'analyze_sound':
            sounds.update(processing_date=datetime.now(), analysis_state="QU")
            transaction.commit_unless_managed()
        self.stdout.write('Updating database done\n')

        # Connect to the Gearman job server.
        if len(jobs) > 0:
            self.stdout.write('Sending %d sound(s) to the gearman queue (%s)\n' % (len(jobs), gearman_task))
            # send them to the queue!
            gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
            gm_client.submit_multiple_jobs(jobs, background=True, wait_until_complete=False)
            self.stdout.write('Sending sounds done')
        else:
            self.stdout.write('no jobs to send')
