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

from general.tasks import DELETE_SPAMMER_USER_ACTION_NAME, FULL_DELETE_USER_ACTION_NAME, DELETE_USER_DELETE_SOUNDS_ACTION_NAME, \
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

    def task_delete_user(self, gearman_worker, gearman_job):
        data = json.loads(gearman_job.data)
        user = User.objects.get(id=data['user_id'])
        deletion_reason = data['deletion_reason']
        workers_logger.info("Start deleting user (%s)" % json.dumps(
            {'task_name': data['action'], 'user_id': user.id, 'username': user.username,
             'deletion_reason': deletion_reason}))
        start_time = time.time()
        try:
            if data['action'] in [FULL_DELETE_USER_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME,
                                  DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_SPAMMER_USER_ACTION_NAME]:

                if data['action'] == DELETE_USER_KEEP_SOUNDS_ACTION_NAME:
                    # This will anonymize the user and will keep the sounds publicly availabe under a "deleted user"
                    # account. A DeletedUser object will be created, but no DeletedSound objects will be created as sound
                    # will be still available. Extra user content (posts, comments, etc) will be preserved but shown as
                    # being authored by a "deleted user".
                    user.profile.delete_user(deletion_reason=deletion_reason)

                elif data['action'] == DELETE_USER_DELETE_SOUNDS_ACTION_NAME:
                    # This will anonymize the user and remove the sounds. A DeletedUser object will be created
                    # as well as DeletedSound objects for each deleted sound, but sounds will no longer be
                    # publicly available. Extra user content (posts, comments, etc) will be preserved but shown as
                    # being authored by a "deleted user".
                    user.profile.delete_user(remove_sounds=True,
                                             deletion_reason=deletion_reason)

                elif data['action'] == DELETE_SPAMMER_USER_ACTION_NAME:
                    # This will completely remove the user object and all of its related data (including sounds)
                    # from the database. A DeletedUser object will be creaetd to keep a record of a user having been
                    # deleted.
                    user.profile.delete_user(delete_user_object_from_db=True,
                                             deletion_reason=deletion_reason)

                elif data['action'] == FULL_DELETE_USER_ACTION_NAME:
                    # This will fully delete the user and the sounds from the database.
                    # WARNING: This functions creates no DeletedSound nor DeletedUser objects and leaves
                    # absolutely no trace about the user.
                    user.delete()

                workers_logger.info("Finished deleting user (%s)" % json.dumps(
                    {'task_name': data['action'], 'user_id': user.id, 'username': user.username,
                     'deletion_reason': deletion_reason, 'work_time': round(time.time() - start_time)}))
                return 'true'

        except Exception as e:
            # This exception is broad but we catch it so that we can log that an error happened.
            # TODO: catching more specific exceptions would be desirable
            workers_logger.error("Unexpected error while deleting user (%s)" % json.dumps(
                {'task_name': data['action'], 'user_id': user.id, 'username': user.username,
                 'deletion_reason': deletion_reason, 'error': str(e), 'work_time': round(time.time() - start_time)}))

        return 'false'

    def task_validate_bulk_describe_csv(self, gearman_worker, gearman_job):
        task_name = 'validate_bulk_describe_csv'
        bulk_upload_progress_object_id = int(gearman_job.data)
        workers_logger.info("Starting validation of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id}))
        start_time = time.time()
        try:
            bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
            bulk.validate_csv_file()
            workers_logger.info("Finished validation of BulkUploadProgress (%s)" % json.dumps(
                {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'work_time': round(time.time() - start_time)}))
            return 'true'
        except BulkUploadProgress.DoesNotExist as e:
            workers_logger.error("Error validating of BulkUploadProgress (%s)" % json.dumps(
                {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'error': str(e),
                 'work_time': round(time.time() - start_time)}))
        return 'false'

    def task_bulk_describe(self, gearman_worker, gearman_job):
        task_name = 'bulk_describe'
        bulk_upload_progress_object_id = int(gearman_job.data)
        workers_logger.info("Starting describing sounds of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id}))
        start_time = time.time()
        try:
            bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
            bulk.describe_sounds()
            bulk.refresh_from_db()  # Refresh from db as describe_sounds() method will change fields of bulk
            bulk.progress_type = 'F'  # Set to finished when one
            bulk.save()
            workers_logger.info("Finished describing sounds of BulkUploadProgress (%s)" % json.dumps(
                {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'work_time': round(time.time() - start_time)}))
            return 'true'
        except BulkUploadProgress.DoesNotExist as e:
            workers_logger.error("Error describing sounds of BulkUploadProgress (%s)" % json.dumps(
                {'task_name': task_name, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                 'error': str(e),
                 'work_time': round(time.time() - start_time)}))
        return 'false'
