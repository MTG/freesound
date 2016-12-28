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

import gearman, sys, traceback, json, time, os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings
from tickets.models import Ticket
from sounds.models import Sound
from optparse import make_option
from utils.mail import send_mail_template
from tickets import TICKET_STATUS_CLOSED
import logging

logger = logging.getLogger("gearman_worker_async_tasks")

class Command(BaseCommand):
    help = 'Run the async tasks worker'

    def write_stdout(self, msg):
        logger.info("[%d] %s" % (os.getpid(),msg))
        self.stdout.write(msg)
        self.stdout.flush()

    def handle(self, *args, **options):
        # N.B. don't take out the print statements as they're
        # very very very very very very very very very very
        # helpful in debugging supervisor+worker+gearman
        self.write_stdout('Initializing gm_worker\n')
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)

        # Read all methods of the class and if it starts with 'task_' then
        # register as a task on gearman
        for task_name in dir(self):
            if task_name.startswith('task_'):
                task_name = str(task_name)
                t_name = task_name.replace('task_', '');
                self.write_stdout('Task: %s\n' % t_name)
                task_func = lambda i:(lambda x, y: getattr(Command, i)(self, x, y))
                gm_worker.register_task(t_name, task_func(task_name))

        self.write_stdout('Starting work\n')
        gm_worker.work()
        self.write_stdout('Ended work\n')

    def task_whitelist_user(self, gearman_worker, gearman_job):
        tickets  = json.loads(gearman_job.data)
        self.write_stdout("Whitelisting users from tickets %i tickets)" % len(tickets))

        count_done = 0
        for ticket_id in tickets:
            ticket = Ticket.objects.get(id=ticket_id)
            whitelist_user = ticket.sender
            if not whitelist_user.profile.is_whitelisted:
                whitelist_user.profile.is_whitelisted = True
                whitelist_user.profile.save()
                self.write_stdout("User %s whitelisted" % whitelist_user.username)

                pending_tickets = Ticket.objects.filter(sender=whitelist_user)\
                                                .exclude(status=TICKET_STATUS_CLOSED)
                # Set all sounds to OK and the tickets to closed
                for pending_ticket in pending_tickets:
                    if pending_ticket.sound:
                        pending_ticket.sound.change_moderation_state("OK")

                    # This could be done with a single update, but there's a chance
                    # we lose a sound that way (a newly created ticket who's sound
                    # is not set to OK, but the ticket is closed).
                    pending_ticket.status = TICKET_STATUS_CLOSED
                    pending_ticket.save()

                count_done = count_done + 1
            self.write_stdout("Finished processing one ticket, %d remaining" % (len(tickets)-count_done))
        return 'true' if len(tickets) == count_done else 'false'

    def task_email_random_sound(self, gearman_worker, gearman_job):
        self.write_stdout("Notifying user of random sound of the day")
        random_sound_id = gearman_job.data
        random_sound = Sound.objects.get(id=random_sound_id)

        send_mail_template(\
                u'One of your sounds has been chosen as random sound of the day!',
                'sounds/email_random_sound.txt',
                {'sound': random_sound, 'user': random_sound.user},
                None, random_sound.user.email)

        self.write_stdout("Finished sending mail to user %s of random sound of the day %s" %
                (random_sound.user, random_sound.id))
        return 'true'

    def task_delete_user(self, gearman_worker, gearman_job):
        self.write_stdout("Started delete_user task ")
        self.write_stdout("Data received: %s" % gearman_job.data)
        data = json.loads(gearman_job.data)
        user = User.objects.get(id=data['user_id'])

        if data['action'] == 'full_db_delete':
            # This will fully delete the user and the sounds from the database.
            # WARNING: Once the sounds are deleted NO DeletedSound object will
            # be created.

            user.delete()
            self.write_stdout("Fully deleted user %d" % data['user_id'])
            return 'true'
        elif data['action'] == 'delete_user_keep_sounds':
            # This will anonymize the user and will keep the sounds publicly
            # availabe

            user.profile.delete_user()
            self.write_stdout("Deleted user %d (sounds kept)" % data['user_id'])
            return 'true'
        elif data['action'] == 'delete_user_delete_sounds':
            # This will anonymize the user and remove the sounds, a
            # DeletedSound object will be created for each sound but kill not
            # be publicly available

            user.profile.delete_user(True)
            self.write_stdout("Deleted user %d and her sounds" % data['user_id'])
            return 'true'

        return 'false'
