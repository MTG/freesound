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
import sentry_sdk

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User

from tickets import TICKET_STATUS_CLOSED
from tickets.models import Ticket, TicketComment
from utils.audioprocessing.freesound_audio_processing import set_timeout_alarm, check_if_free_space, \
    FreesoundAudioProcessor, WorkerException, cancel_timeout_alarm, FreesoundAudioProcessorBeforeDescription
from utils.cache import invalidate_user_template_caches, invalidate_all_moderators_header_cache


workers_logger = logging.getLogger("workers")

WHITELIST_USER_TASK_NAME = 'whitelist_user'
POST_MODERATION_ASSIGNED_TICKETS_TASK_NAME = "post_moderation_assigned_tickets"
DELETE_USER_TASK_NAME = 'delete_user'
VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME = "validate_bulk_describe_csv"
BULK_DESCRIBE_TASK_NAME = "bulk_describe"
PROCESS_ANALYSIS_RESULTS_TASK_NAME = "process_analysis_results"
SOUND_PROCESSING_TASK_NAME = "process_sound"
PROCESS_BEFORE_DESCRIPTION_TASK_NAME = "process_before_description"

DELETE_SPAMMER_USER_ACTION_NAME = 'delete_user_spammer'
FULL_DELETE_USER_ACTION_NAME = 'full_delete_user'
DELETE_USER_DELETE_SOUNDS_ACTION_NAME = 'delete_user_delete_sounds'
DELETE_USER_KEEP_SOUNDS_ACTION_NAME = 'delete_user_keep_sounds'


@shared_task(name=WHITELIST_USER_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def whitelist_user(ticket_ids=None, user_id=None):
    # Whitelist "sender" users from the tickets with given ids
    workers_logger.info("Start whitelisting users from tickets (%s)" % json.dumps({
        'task_name': WHITELIST_USER_TASK_NAME, 
        'n_tickets': len(ticket_ids) if ticket_ids is not None else 0, 
        'user_id': user_id if user_id is not None else ''})) 
    start_time = time.time()
    count_done = 0

    users_to_whitelist_ids = []

    if ticket_ids is not None:
        for ticket_id in ticket_ids:
            ticket = Ticket.objects.get(id=ticket_id)
            users_to_whitelist_ids.append(ticket.sender.id)

    if user_id is not None:
        users_to_whitelist_ids.append(user_id)

    users_to_whitelist_ids = list(set(users_to_whitelist_ids))    
    users_to_whitelist = User.objects.filter(id__in=users_to_whitelist_ids).select_related('profile')
    for whitelist_user in users_to_whitelist:
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

            # Invalidate template caches for sender user
            invalidate_user_template_caches(whitelist_user.id)

            workers_logger.info("Whitelisted user (%s)" % json.dumps(
                {'user_id': whitelist_user.id,
                 'username': whitelist_user.username,
                 'work_time': round(time.time() - local_start_time)}))

        count_done = count_done + 1

    # Invalidate template caches for moderators
    invalidate_all_moderators_header_cache()

    workers_logger.info("Finished whitelisting users from tickets (%s)" % json.dumps(
        {'task_name': WHITELIST_USER_TASK_NAME, 
         'n_tickets': len(ticket_ids) if ticket_ids is not None else 0, 
         'user_id': user_id if user_id is not None else '',
         'work_time': round(time.time() - start_time)}))


@shared_task(name=POST_MODERATION_ASSIGNED_TICKETS_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def post_moderation_assigned_tickets(ticket_ids=[], notification=None, msg=False, moderator_only=False, users_to_update=None, packs_to_update=None):
    # Carry out post-processing tasks for the approved sounds like invlaidating caches, sending packs to process, etc...
    # We do that in an async task to avoid moderation requests taking too long when approving sounds
    workers_logger.info("Start post moderation assigned tickets (%s)" % json.dumps({
        'task_name': POST_MODERATION_ASSIGNED_TICKETS_TASK_NAME, 
        'n_tickets': len(ticket_ids)})) 
    start_time = time.time()
    tickets = Ticket.objects.filter(id__in=ticket_ids)

    collect_users_and_packs = False
    if not users_to_update and not packs_to_update:
        collect_users_and_packs = True
        users_to_update = set()
        packs_to_update = set()

    for ticket in tickets:
        if collect_users_and_packs:
            # Collect list of users and packls to update
            # We only fill here users_to_update and packs_to_update if action is not
            # "Delete". See comment in "Delete" action case some lines above
            users_to_update.add(ticket.sound.user_id)
            if ticket.sound.pack:
                packs_to_update.add(ticket.sound.pack_id)
        
        # Invalidate caches of related objects
        invalidate_user_template_caches(ticket.sender.id)
        invalidate_all_moderators_header_cache()

        # Add new comments to the ticket
        if msg:
            tc = TicketComment(sender=ticket.assignee,
                               text=msg,
                               ticket=ticket,
                               moderator_only=moderator_only)
            tc.save()

        # Send notification email to users
        if notification is not None:
            ticket.send_notification_emails(notification, Ticket.USER_ONLY)

    # Update number of sounds for each user
    Profile = apps.get_model('accounts.Profile')
    for profile in Profile.objects.filter(user_id__in=list(users_to_update)):
        profile.update_num_sounds()

    # Process packs
    Pack = apps.get_model('sounds.Pack')
    for pack in Pack.objects.filter(id__in=list(packs_to_update)):
        pack.process()

    workers_logger.info("Finished post moderation assigned tickets (%s)" % json.dumps(
        {'task_name': POST_MODERATION_ASSIGNED_TICKETS_TASK_NAME, 
         'n_tickets': len(ticket_ids), 
         'work_time': round(time.time() - start_time)}))


@shared_task(name=DELETE_USER_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def delete_user(user_id, deletion_action, deletion_reason):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        workers_logger.info("Can't delete user as it does not exist (%s)" % json.dumps(
            {'task_name': deletion_action, 'user_id': user_id, 'username': '-',
             'deletion_reason': deletion_reason}))
        return

    username_before_deletion = user.username
    workers_logger.info("Start deleting user (%s)" % json.dumps(
        {'task_name': deletion_action, 'user_id': user_id, 'username': username_before_deletion,
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
                {'task_name': deletion_action, 'user_id': user.id, 'username': username_before_deletion,
                 'deletion_reason': deletion_reason, 'work_time': round(time.time() - start_time)}))

    except Exception as e:
        # This exception is broad but we catch it so that we can log that an error happened.
        # TODO: catching more specific exceptions would be desirable
        workers_logger.info("Unexpected error while deleting user (%s)" % json.dumps(
            {'task_name': deletion_action, 'user_id': user.id, 'username': username_before_deletion,
             'deletion_reason': deletion_reason, 'error': str(e), 'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly


@shared_task(name=VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def validate_bulk_describe_csv(bulk_upload_progress_object_id):
    # Import BulkUploadProgress model from apps to avoid circular dependency
    BulkUploadProgress = apps.get_model('sounds.BulkUploadProgress')

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
        workers_logger.info("Error validating of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': VALIDATE_BULK_DESCRIBE_CSV_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'error': str(e),
                'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly


@shared_task(name=BULK_DESCRIBE_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def bulk_describe(bulk_upload_progress_object_id):
    # Import BulkUploadProgress model from apps to avoid circular dependency
    BulkUploadProgress = apps.get_model('sounds.BulkUploadProgress')

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
        workers_logger.info("Error describing sounds of BulkUploadProgress (%s)" % json.dumps(
            {'task_name': BULK_DESCRIBE_TASK_NAME, 'bulk_upload_progress_id': bulk_upload_progress_object_id,
                'error': str(e),
                'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly


@shared_task(name=PROCESS_ANALYSIS_RESULTS_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
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
    # Import SoundAnalysis model from apps to avoid circular dependency
    SoundAnalysis = apps.get_model('sounds.SoundAnalysis')

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
            # Load analysis output to database field (following configuration in settings.ANALYZERS_CONFIGURATION)
            a.load_analysis_data_from_file_to_db()
            
            if analyzer in settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS or analyzer in settings.ANALYZERS_CONFIGURATION:
                # If the analyzer produces data that should be indexed in the search engine, set sound index to dirty so that the sound gets reindexed soon
                a.sound.mark_index_dirty(commit=True)
            workers_logger.info("Finished processing analysis results (%s)" % json.dumps(
                {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status,
                 'work_time': round(time.time() - start_time)}))

    except (SoundAnalysis.DoesNotExist, Exception) as e:
        workers_logger.info("Error processing analysis results (%s)" % json.dumps(
                {'task_name': PROCESS_ANALYSIS_RESULTS_TASK_NAME, 'sound_id': sound_id, 'analyzer': analyzer, 'status': status,
                 'error': str(e), 'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly


@shared_task(name=SOUND_PROCESSING_TASK_NAME, queue=settings.CELERY_SOUND_PROCESSING_QUEUE_NAME)
def process_sound(sound_id, skip_previews=False, skip_displays=False):
    """Process a sound and generate the mp3/ogg preview files and the waveform/spectrogram displays

    Args:
        sound_id (int): ID of the sound to process
        skip_previews (bool): set to True for skipping the computation of previews
        skip_displays (bool): set to True for skipping the computation of images
    """
    # Import Sound model from apps to avoid circular dependency
    Sound = apps.get_model('sounds.Sound')

    set_timeout_alarm(settings.WORKER_TIMEOUT, f'Processing of sound {sound_id} timed out')
    workers_logger.info("Starting processing of sound (%s)" % json.dumps({
        'task_name': SOUND_PROCESSING_TASK_NAME, 'sound_id': sound_id}))
    start_time = time.time()
    try:
        check_if_free_space()
        result = FreesoundAudioProcessor(sound_id=sound_id) \
            .process(skip_displays=skip_displays, skip_previews=skip_previews)
        if result:
            workers_logger.info("Finished processing of sound (%s)" % json.dumps(
                {'task_name': SOUND_PROCESSING_TASK_NAME, 'sound_id': sound_id, 'result': 'success',
                 'work_time': round(time.time() - start_time)}))
        else:
            workers_logger.info("Finished processing of sound (%s)" % json.dumps(
                {'task_name': SOUND_PROCESSING_TASK_NAME, 'sound_id': sound_id, 'result': 'failure',
                 'work_time': round(time.time() - start_time)}))

    except WorkerException as e:
        try:
            sound = Sound.objects.get(id=sound_id)
            sound.set_processing_ongoing_state("FI")
            sound.change_processing_state("FA", processing_log=str(e))
        except Sound.DoesNotExist:
            pass
        workers_logger.info("WorkerException while processing sound (%s)" % json.dumps(
            {'task_name': SOUND_PROCESSING_TASK_NAME, 'sound_id': sound_id, 'error': str(e),
             'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly

    except Exception as e:
        try:
            sound = Sound.objects.get(id=sound_id)
            sound.set_processing_ongoing_state("FI")
            sound.change_processing_state("FA", processing_log=str(e))
        except Sound.DoesNotExist:
            pass
        workers_logger.info("Unexpected error while processing sound (%s)" % json.dumps(
            {'task_name': SOUND_PROCESSING_TASK_NAME, 'sound_id': sound_id, 'error': str(e),
             'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly

    cancel_timeout_alarm()


@shared_task(name=PROCESS_BEFORE_DESCRIPTION_TASK_NAME, queue=settings.CELERY_ASYNC_TASKS_QUEUE_NAME)
def process_before_description(audio_file_path):
    """Processes an uploaed sound file before the sound is described and saves generated previews
    and wave/spectral images in a specfic directory so these can be served in the sound players
    used in the description phase.

    Args:
        audio_file_path (str): path to the uploaded file
    """
    set_timeout_alarm(settings.WORKER_TIMEOUT, f'Processing-before-describe of sound {audio_file_path} timed out')
    workers_logger.info("Starting processing-before-describe of sound (%s)" % json.dumps({
        'task_name': PROCESS_BEFORE_DESCRIPTION_TASK_NAME, 'audio_file_path': audio_file_path}))
    start_time = time.time()
    try:
        check_if_free_space()
        result = FreesoundAudioProcessorBeforeDescription(audio_file_path=audio_file_path).process()
        if result:
            workers_logger.info("Finished processing-before-describe of sound (%s)" % json.dumps(
                {'task_name': PROCESS_BEFORE_DESCRIPTION_TASK_NAME, 'audio_file_path': audio_file_path, 'result': 'success',
                 'work_time': round(time.time() - start_time)}))
        else:
            workers_logger.info("Finished processing-before-describe of sound (%s)" % json.dumps(
                {'task_name': PROCESS_BEFORE_DESCRIPTION_TASK_NAME, 'audio_file_path': audio_file_path, 'result': 'failure',
                 'work_time': round(time.time() - start_time)}))

    except WorkerException as e:
        workers_logger.info("WorkerException while processing-before-describe sound (%s)" % json.dumps(
            {'task_name': PROCESS_BEFORE_DESCRIPTION_TASK_NAME, 'audio_file_path': audio_file_path, 'error': str(e),
             'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly

    except Exception as e:
        workers_logger.info("Unexpected error while processing-before-describe sound (%s)" % json.dumps(
            {'task_name': PROCESS_BEFORE_DESCRIPTION_TASK_NAME, 'audio_file_path': audio_file_path, 'error': str(e),
             'work_time': round(time.time() - start_time)}))
        sentry_sdk.capture_exception(e)  # Manually capture exception so it has mroe info and Sentry can organize it properly

    cancel_timeout_alarm()