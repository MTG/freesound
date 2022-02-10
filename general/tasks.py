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
import datetime
import json
import logging
import time

from celery.decorators import task
from django.conf import settings
from django.contrib.auth.models import User

from accounts.admin import DELETE_SPAMMER_USER_ACTION_NAME
from accounts.admin import FULL_DELETE_USER_ACTION_NAME, DELETE_USER_DELETE_SOUNDS_ACTION_NAME, \
    DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from sounds.models import BulkUploadProgress, SoundAnalysis
from tickets import TICKET_STATUS_CLOSED
from tickets.models import Ticket

workers_logger = logging.getLogger("workers")

WHITELIST_USER_TASK_NAME = 'whitelist_user'
DELETE_USER_TASK_NAME = 'delete_user'
VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME = "validate_bulk_describe_csv"
BULK_DESCRIBE_TASK_NAME = "bulk_describe"
PROCESS_ANALYSIS_RESULTS_TASK_NAME = "process_analysis_results"


@task(name=WHITELIST_USER_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def whitelist_user(ticket_ids):
    workers_logger.info("Start whitelisting users from tickets (%s)" % json.dumps({
        'task_name': WHITELIST_USER_TASK_NAME, 'n_tickets': len(ticket_ids)}))
    start_time = time.time()
    count_done = 0
    for ticket_id in ticket_ids:
        ticket = Ticket.objects.get(id=ticket_id)
        whitelist_user = ticket.sender
        if not whitelist_user.profile.is_whitelisted:
            local_start_time = time.time()
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
                    'work_time': round(time.time() - local_start_time)}))

        count_done = count_done + 1

    workers_logger.info("Finished whitelisting users from tickets (%s)" % json.dumps(
        {'task_name': WHITELIST_USER_TASK_NAME, 'n_tickets': len(ticket_ids), 'work_time': round(time.time() - start_time)}))


@task(name=DELETE_USER_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def delete_user(user_id, deletion_action, deletion_reason):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        workers_logger.info("Can't delete user as it does not exist (%s)" % json.dumps(
            {'task_name': deletion_action, 'user_id': user_id, 'username': '-',
                'deletion_reason': deletion_reason}))
        return
    
    workers_logger.info("Start deleting user (%s)" % json.dumps(
        {'task_name': deletion_action, 'user_id': user_id, 'username': user.username,
            'deletion_reason': deletion_reason}))
    start_time = time.time()
    try:
        if deletion_action in [FULL_DELETE_USER_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME,
                                DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_SPAMMER_USER_ACTION_NAME]:

            if deletion_action == DELETE_USER_KEEP_SOUNDS_ACTION_NAME:
                # This will anonymize the user and will keep the sounds publicly availabe under a "deleted user"
                # account. A DeletedUser object will be created, but no DeletedSound objects will be created as sound
                # will be still available. Extra user content (posts, comments, etc) will be preserved but shown as
                # being authored by a "deleted user".
                user.profile.delete_user(deletion_reason=deletion_reason)

            elif deletion_action == DELETE_USER_DELETE_SOUNDS_ACTION_NAME:
                # This will anonymize the user and remove the sounds. A DeletedUser object will be created
                # as well as DeletedSound objects for each deleted sound, but sounds will no longer be
                # publicly available. Extra user content (posts, comments, etc) will be preserved but shown as
                # being authored by a "deleted user".
                user.profile.delete_user(remove_sounds=True,
                                            deletion_reason=deletion_reason)

            elif deletion_action == DELETE_SPAMMER_USER_ACTION_NAME:
                # This will completely remove the user object and all of its related data (including sounds)
                # from the database. A DeletedUser object will be creaetd to keep a record of a user having been
                # deleted.
                user.profile.delete_user(delete_user_object_from_db=True,
                                            deletion_reason=deletion_reason)

            elif deletion_action == FULL_DELETE_USER_ACTION_NAME:
                # This will fully delete the user and the sounds from the database.
                # WARNING: This functions creates no DeletedSound nor DeletedUser objects and leaves
                # absolutely no trace about the user.
                user.delete()

            workers_logger.info("Finished deleting user (%s)" % json.dumps(
                {'task_name': deletion_action, 'user_id': user.id, 'username': user.username,
                    'deletion_reason': deletion_reason, 'work_time': round(time.time() - start_time)}))

    except Exception as e:
        # This exception is broad but we catch it so that we can log that an error happened.
        # TODO: catching more specific exceptions would be desirable
        workers_logger.error("Unexpected error while deleting user (%s)" % json.dumps(
            {'task_name': deletion_action, 'user_id': user.id, 'username': user.username,
                'deletion_reason': deletion_reason, 'error': str(e), 'work_time': round(time.time() - start_time)}))


@task(name=VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def validate_bulk_describe_csv(bulk_upload_progress_object_id):
    workers_logger.info("Starting validation of BulkUploadProgress (%s)" % json.dumps(
        {'task_name': VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id}))
    start_time = time.time()
    try:
        bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
        bulk.validate_csv_file()
        workers_logger.info("Finished validation of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'work_time': round(time.time() - start_time)}))
    
    except BulkUploadProgress.DoesNotExist as e:
        workers_logger.error("Error validating of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'error': str(e),
                'work_time': round(time.time() - start_time)}))
    

@task(name=BULK_DESCRIBE_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def bulk_describe(bulk_upload_progress_object_id):
    workers_logger.info("Starting describing sounds of BulkUploadProgress (%s)" % json.dumps(
        {'task_name': BULK_DESCRIBE_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id}))
    start_time = time.time()
    try:
        bulk = BulkUploadProgress.objects.get(id=bulk_upload_progress_object_id)
        bulk.describe_sounds()
        bulk.refresh_from_db()  # Refresh from db as describe_sounds() method will change fields of bulk
        bulk.progress_type = 'F'  # Set to finished when one
        bulk.save()
        workers_logger.info("Finished describing sounds of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': BULK_DESCRIBE_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'work_time': round(time.time() - start_time)}))
    
    except BulkUploadProgress.DoesNotExist as e:
        workers_logger.error("Error describing sounds of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': BULK_DESCRIBE_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'error': str(e),
                'work_time': round(time.time() - start_time)}))


@task(name=PROCESS_ANALYSIS_RESULTS_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def process_analysis_results(sound_id, analyzer, status, analysis_time, exception=None):
    """Process the results of the analysis of a file and update the SoundAnalysis object accordingly.

    This is a celery task that gets called by the analysis workers when they finish the analysis job. This task checks
    the results and updates the corresponding SoundAnalysis object to update the status, modification date, analysis
    time, analysis data, etc...

    Args:
        sound_id (int): ID of the sound that has been analyzed
        analyzer (str): name of the analyzer that was used to analyze the sound
        status (str): status after the analysis job has finished. Should be one of "OK" for ok analysis, "FA" for
            failed analysis, or "SK" for analysis that were skipped (e.g. because a file was too long or some other
            reason decided by the analyzer).
        analysis_time (float): the time it took in seconds for the analyzer to carry out the analysis task
        exception (str): error message in case there was an error
    """
    workers_logger.info("Starting processing analysis results (%s)" % json.dumps(
        {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status}))
    start_time = time.time()
    try:
        # Analysis happens in a different celery worker, here we just save the results in a SoundAnalysis object
        a = SoundAnalysis.objects.get(sound_id=sound_id, analyzer=analyzer)

        # Update status and queued fields. No need to update "created" as it is done automatically by Django
        a.analysis_status = status
        a.analysis_time = analysis_time
        a.last_analyzer_finished = datetime.datetime.now()
        a.save(update_fields=['analysis_status', 'last_analyzer_finished', 'analysis_time'])
        if exception:
            workers_logger.info("Finished processing analysis results (%s)" % json.dumps(
                {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status,
                 'exception': str(exception), 'work_time': round(time.time() - start_time)}))
        else:
            # Load analysis output to database field (following configuration  in settings.ANALYZERS_CONFIGURATION)
            a.load_analysis_data_from_file_to_db()
            # Set sound to index dirty so that the sound gets reindexed with updated analysis fields
            a.sound.mark_index_dirty(commit=True)
            workers_logger.info("Finished processing analysis results (%s)" % json.dumps(
                {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status,
                 'work_time': round(time.time() - start_time)}))

    except (SoundAnalysis.DoesNotExist, Exception) as e:
        workers_logger.error("Finished processing analysis results (%s)" % json.dumps(
                {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status,
                 'error': str(e), 'work_time': round(time.time() - start_time)}))
