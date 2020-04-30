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

import json
import logging
import time

import gearman
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.admin import FULL_DELETE_USER_ACTION_NAME, DELETE_USER_DELETE_SOUNDS_ACTION_NAME, \
    DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from sounds.models import BulkUploadProgress
from tickets import TICKET_STATUS_CLOSED
from tickets.models import Ticket

workers_logger = logging.getLogger('workers')


class Command(BaseCommand):
    help = 'Run the async tasks worker'

    def handle(self, *args, **options):
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        registered_tasks = []
        for task_name in dir(self):
            if task_name.startswith('task_'):
                task_name = str(task_name)
                t_name = task_name.replace('task_', '');
                task_func = lambda i: (lambda x, y: getattr(Command, i)(self, x, y))
                gm_worker.register_task(t_name, task_func(task_name))
                registered_tasks.append(t_name)

        workers_logger.info('Started worker with tasks: %s' % ', '.join(registered_tasks))
        gm_worker.work()

    def task_whitelist_user(self, gearman_worker, gearman_job):
        tickets = json.loads(gearman_job.data)
        workers_logger.info("Start whitelisting users from tickets (%s)" % json.dumps({'n_tickets': len(tickets)}))
        starttime = time.time()
        count_done = 0
        for ticket_id in tickets:
            ticket = Ticket.objects.get(id=ticket_id)
            whitelist_user = ticket.sender
            if not whitelist_user.profile.is_whitelisted:
                local_starttime = time.time()
                whitelist_user.profile.is_whitelisted = True
                whitelist_user.profile.save()
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

                workers_logger.info("Whitelisted user (%s)" % json.dumps(
                    {'user_id': whitelist_user.id,
                     'username': whitelist_user.username,
                     'work_time': time.time() - local_starttime}))

            count_done = count_done + 1

        workers_logger.info("Finished whitelisting users from tickets (%s)" % json.dumps(
            {'n_tickets': len(tickets), 'work_time': time.time() - starttime}))
        return 'true' if len(tickets) == count_done else 'false'

    def task_delete_user(self, gearman_worker, gearman_job):
        data = json.loads(gearman_job.data)
        user = User.objects.get(id=data['user_id'])
        workers_logger.info("Start deleting user (%s)" % json.dumps(
            {'user_id': user.id, 'username': user.username, 'delete_type': data['action']}))
        starttime = time.time()
        try:
            if data['action'] in [FULL_DELETE_USER_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME,
                                  DELETE_USER_DELETE_SOUNDS_ACTION_NAME]:

                if data['action'] == FULL_DELETE_USER_ACTION_NAME:
                    # This will fully delete the user and the sounds from the database.
                    # WARNING: Once the sounds are deleted NO DeletedSound object will
                    # be created.
                    user.delete()

                elif data['action'] == DELETE_USER_KEEP_SOUNDS_ACTION_NAME:
                    # This will anonymize the user and will keep the sounds publicly
                    # availabe
                    user.profile.delete_user()

                elif data['action'] == DELETE_USER_DELETE_SOUNDS_ACTION_NAME:
                    # This will anonymize the user and remove the sounds, a
                    # DeletedSound object will be created for each sound but kill not
                    # be publicly available
                    user.profile.delete_user(True)

                workers_logger.info("Finished deleting user (%s)" % json.dumps(
                    {'user_id': user.id, 'username': user.username, 'delete_type': data['action'],
                     'work_time': time.time() - starttime}))
                return 'true'

        except Exception as e:
            # This exception is broad but we catch it so that we can log that an error happened.
            # TODO: catching more specific exceptions would be desirable
            workers_logger.error("Unexpected error while deleting user (%s)" % json.dumps(
                {'user_id': user.id, 'username': user.username, 'delete_type': data['action'], 'error': str(e),
                 'work_time': time.time() - starttime}))

        return 'false'

    def task_validate_bulk_describe_csv(self, gearman_worker, gearman_job):
        bulk_upload_progress_object_id = int(gearman_job.data)
        workers_logger.info("Starting validation of BulkUploadProgress (%s)" % json.dumps(
            {'bulk_upload_progress_id': bulk_upload_progress_object_id}))
        starttime = time.time()
        try:
            bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
            bulk.validate_csv_file()
            workers_logger.info("Finished validation of BulkUploadProgress (%s)" % json.dumps(
                {'bulk_upload_progress_id': bulk_upload_progress_object_id, 'work_time': time.time() - starttime}))
            return 'true'
        except BulkUploadProgress.DoesNotExist as e:
            workers_logger.error("Error validating of BulkUploadProgress (%s)" % json.dumps(
                {'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'error': str(e),
                 'work_time': time.time() - starttime}))
        return 'false'

    def task_bulk_describe(self, gearman_worker, gearman_job):
        bulk_upload_progress_object_id = int(gearman_job.data)
        workers_logger.info("Starting describing sounds of BulkUploadProgress (%s)" % json.dumps(
            {'bulk_upload_progress_id': bulk_upload_progress_object_id}))
        starttime = time.time()
        try:
            bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
            bulk.describe_sounds()
            bulk.refresh_from_db()  # Refresh from db as describe_sounds() method will change fields of bulk
            bulk.progress_type = 'F'  # Set to finished when one
            bulk.save()
            workers_logger.info("Finished describing sounds of BulkUploadProgress (%s)" % json.dumps(
                {'bulk_upload_progress_id': bulk_upload_progress_object_id, 'work_time': time.time() - starttime}))
            return 'true'
        except BulkUploadProgress.DoesNotExist as e:
            workers_logger.error("Error describing sounds of BulkUploadProgress (%s)" % json.dumps(
                {'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'error': str(e),
                 'work_time': time.time() - starttime}))
        return 'false'
