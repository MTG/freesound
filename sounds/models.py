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

from past.utils import old_div
import datetime
import glob
import json
import logging
import math
import os
import random
import yaml
import zlib

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import F
from django.db.models.functions import Greatest
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.text import Truncator, slugify

import accounts.models
from apiv2.models import ApiV2Client
from comments.models import Comment
from freesound.celery import app as celery_app
from general import tasks
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from ratings.models import SoundRating
from tags.models import TaggedItem, Tag
from tickets import TICKET_STATUS_CLOSED, TICKET_STATUS_NEW
from tickets.models import Ticket, Queue, TicketComment
from utils.cache import invalidate_template_cache
from utils.locations import locations_decorator
from utils.mail import send_mail_template
from utils.search import get_search_engine, SearchEngineException
from utils.search.search_sounds import delete_sounds_from_search_engine
from utils.similarity_utilities import delete_sound_from_gaia
from utils.sound_upload import get_csv_lines, validate_input_csv_file, bulk_describe_from_csv

web_logger = logging.getLogger('web')
sounds_logger = logging.getLogger('sounds')


class License(OrderedModel):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=8, db_index=True)
    summary = models.TextField()
    short_summary = models.TextField(null=True)
    deed_url = models.URLField()
    legal_code_url = models.URLField()
    is_public = models.BooleanField(default=True)

    def get_short_summary(self):
        return self.short_summary if self.short_summary is not None else Truncator(self.summary)\
            .words(20, html=True, truncate='...')

    @property
    def name_with_version(self):
        version_label = ''
        if '3.0' in self.deed_url:
            version_label = ' 3.0'
        elif '4.0' in self.deed_url:
            version_label = ' 4.0'
        name = self.name
        if name == 'Attribution Noncommercial':
            # For dipslaying purposes, we make the name shorter, otherwise it overflows in BW sound page
            name = 'Noncommercial'
        return f'{name}{version_label}'

    def __str__(self):
        return self.name_with_version


class BulkUploadProgress(models.Model):
    """Store progress status for a Bulk Describe process."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    CSV_CHOICES = (
        ("N", 'Not yet validated'),  # linked CSV file has not yet been validated
        ("F", 'Finished description'),   # All sounds have been described/created (but some might still be in
                                         # processing/moderation stage)
        ("S", 'Sounds being described and processed'),  # Description (and processing) process has started
        ("V", 'Finished validation'),  # CSV file has been validated (might have errors)
        ("C", 'Closed'),  # Process has finished and has been closes
    )
    progress_type = models.CharField(max_length=1, choices=CSV_CHOICES, default="N")
    csv_filename = models.CharField(max_length=512, null=True, blank=True, default=None)
    original_csv_filename = models.CharField(max_length=255)
    validation_output = JSONField(null=True)
    sounds_valid = models.PositiveIntegerField(null=False, default=0)
    description_output = JSONField(null=True)

    @property
    def csv_path(self):
        directory = os.path.join(settings.CSV_PATH, str(self.user.id))
        return os.path.join(directory, self.csv_filename)

    def get_bulk_upload_basic_data_for_log(self):
        return {
            'bulk_upload_id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'original_csv_filename': self.original_csv_filename,
            'csv_path': self.csv_path
        }

    def get_csv_lines(self):
        """
        Read lines form CSV file and return a tuple with the header and a list of dictionaries.
        """
        return get_csv_lines(self.csv_path)

    def validate_csv_file(self):
        """
        Validate CSV file and store output in self.validation_output.
        """
        header, lines = self.get_csv_lines()
        bulk_upload_basic_data = self.get_bulk_upload_basic_data_for_log()
        try:
            lines_validated, global_errors = validate_input_csv_file(
                csv_header=header,
                csv_lines=lines,
                sounds_base_dir=os.path.join(settings.UPLOADS_PATH, str(self.user_id)),
                username=self.user.username)
        except Exception:
            # This is a broad exception clause intentionally placed here to make sure that BulkUploadProgress is
            # updated with a global error. Otherwise it will appear to the user that the object is permanently being
            # validated. After we update the object with the "unexpected error" message, we log the exception and
            # continue with excecution
            lines_validated = []
            global_errors = ['An unexpected error occurred while validating your data file']

        self.validation_output = {
            'lines_ok': [line for line in lines_validated if not line['line_errors']],
            'lines_with_errors': [line for line in lines_validated if line['line_errors']],
            'global_errors': global_errors,
        }
        self.progress_type = 'V'  # Set progress to 'validated'
        self.save()

        # Log information about the process
        bulk_upload_basic_data.update({
            'n_lines_ok': len(self.validation_output['lines_ok']),
            'n_lines_with_errors': len(self.validation_output['lines_with_errors']),
            'n_global_errors': len(self.validation_output['global_errors']),
        })
        web_logger.info(f'Validated data file for bulk upload ({json.dumps(bulk_upload_basic_data)})')

    def describe_sounds(self):
        """
        Start the actual description of the sounds and add them to Freesound.
        """
        bulk_upload_basic_data = self.get_bulk_upload_basic_data_for_log()
        web_logger.info(f'Started creating sound objects for bulk upload ({json.dumps(bulk_upload_basic_data)})')
        bulk_describe_from_csv(
            self.csv_path,
            delete_already_existing=False,
            force_import=True,
            sounds_base_dir=os.path.join(settings.UPLOADS_PATH, str(self.user_id)),
            username=self.user.username,
            bulkupload_progress_id=self.id)
        web_logger.info(f'Finished creating sound objects for bulk upload ({json.dumps(bulk_upload_basic_data)})')

    def store_progress_for_line(self, line_no, message):
        """
        Store the description progress of individual lines.
        """
        if self.description_output is None:
            self.description_output = {}
        self.description_output[line_no] = message
        self.save()

    def get_description_progress_info(self):
        """
        Get information about the progress of the description process and the status of the sounds that have already
        been successfully described so that it can be shown to users.
        """
        sound_ids_described_ok = []
        sound_errors = []
        if self.description_output is not None:
            for line_no, value in self.description_output.items():
                if isinstance(value, int):
                    # Sound id, meaning a file for which a Sound object was successfully created
                    sound_ids_described_ok.append(value)
                else:
                    # If not sound ID, then it means there were errors with these sounds
                    sound_errors.append((line_no, value))
        n_sounds_described_ok = len(sound_ids_described_ok)
        n_sounds_error = len(sound_errors)
        n_lines_validated_ok = len(self.validation_output['lines_ok']) if self.validation_output is not None else 0
        n_sounds_remaining_to_describe = n_lines_validated_ok - n_sounds_described_ok - n_sounds_error

        n_sounds_published = Sound.objects.filter(
            id__in=sound_ids_described_ok, processing_state="OK", moderation_state="OK").count()
        n_sounds_moderation = Sound.objects.filter(
            id__in=sound_ids_described_ok, processing_state="OK").exclude(moderation_state="OK").count()
        n_sounds_currently_processing = Sound.objects.filter(
            id__in=sound_ids_described_ok, processing_state="PE", processing_ongoing_state="PR").count()
        n_sounds_pending_processing = Sound.objects.filter(
            id__in=sound_ids_described_ok, processing_state="PE").exclude(processing_ongoing_state="PR").count()
        n_sounds_failed_processing = Sound.objects.filter(
            id__in=sound_ids_described_ok, processing_state="FA").count()

        # The remaining sounds that have been described ok but do not appear in any of the sets above are sounds with
        # an unknown state. This could happen if sounds get deleted (e.g. as part of the moderation process or because
        # a sound fails processing and the user deletes it).
        n_sounds_unknown = n_sounds_described_ok - (n_sounds_published +
                                                    n_sounds_moderation +
                                                    n_sounds_currently_processing +
                                                    n_sounds_pending_processing +
                                                    n_sounds_failed_processing)
        progress = 0
        if self.description_output is not None:
            progress = old_div(100.0 * (n_sounds_published +
                                n_sounds_moderation +
                                n_sounds_failed_processing +
                                n_sounds_error +
                                n_sounds_unknown), \
                       (n_sounds_described_ok +
                        n_sounds_error +
                        n_sounds_remaining_to_describe))
            progress = int(progress)
            # NOTE: progress percentage is determined as the total number of sounds "that won't change" vs the total
            # number of sounds that should have been described and processed. Sounds that fail processing or description
            # are also counted as "done" as their status won't change.
            # After the 'describe_sounds' method finishes, progress should always be 100.

        return {
            'n_sounds_remaining_to_describe': n_sounds_remaining_to_describe,
            'n_sounds_described_ok': n_sounds_described_ok,
            'sound_errors': sound_errors,
            'n_sounds_error': n_sounds_error,
            'n_sounds_published': n_sounds_published,
            'n_sounds_moderation': n_sounds_moderation,
            'n_sounds_pending_processing': n_sounds_pending_processing,
            'n_sounds_currently_processing': n_sounds_currently_processing,
            'n_sounds_processing': n_sounds_pending_processing + n_sounds_currently_processing,
            'n_sounds_failed_processing': n_sounds_failed_processing,
            'n_sounds_unknown': n_sounds_unknown,
            'progress_percentage': progress,
        }

    def has_global_validation_errors(self):
        """
        Returns True if the validation finished with global errors
        """
        if self.validation_output is not None:
            return len(self.validation_output['global_errors']) > 0
        return False

    def has_line_validation_errors(self):
        """
        Returns True if some errors were found in line validation
        """
        if self.validation_output is not None:
            return len(self.validation_output['lines_with_errors']) > 0
        return False

    class Meta:
        permissions = (
            ("can_describe_in_bulk", "Can use the Bulk Describe feature."),
        )


class SoundManager(models.Manager):

    def latest_additions(self, num_sounds, period_days=2):
        if settings.DEBUG:
            # In DEBUG mode we probably won't have any sounds from the requested period, so we
            # see what the most recent sound and go back from then instead
            latest_sound = Sound.public.order_by('-created').first()
            date_threshold = latest_sound.created
        else:
            date_threshold = datetime.datetime.now()

        date_threshold = date_threshold - datetime.timedelta(days=period_days)

        # We leave the `greatest(created, moderation_date)` condition in the query because in combination
        # with an index in the table this give us fast lookups. If we remove it, postgres resorts to
        # a table scan.
        query = """
                select
                    user_id,
                    id,
                    n_other_sounds
                from (
                select
                    user_id,
                    max(id) as id,
                    greatest(max(created), max(moderation_date)) as created,
                    count(*) - 1 as n_other_sounds
                from
                    sounds_sound
                where
                    processing_state = 'OK' and
                    moderation_state = 'OK'
                    and greatest(created, moderation_date) > %s
                group by
                    user_id
                ) as X order by created desc limit %s"""
        return self.raw(query, (date_threshold.isoformat(), num_sounds))

    def random(self, excludes=None):
        """ Select a random sound from the database which is suitable for display.
        Random sounds must fall under the following criteria:
           - Not Explicit
           - Moderated and processed
           - Not flagged
           - At least 3 ratings and an average rating of >6
        Additionally, an optional set of `excludes` can be specified
        to disallow sounds which match this criteria."""
        query_sounds = self.exclude(is_explicit=True)\
            .filter(moderation_state="OK",
                    processing_state="OK",
                    flag=None,
                    avg_rating__gt=6,
                    num_ratings__gt=3)
        if excludes:
            query_sounds = query_sounds.exclude(**excludes)
        sound_count = query_sounds.count()
        if sound_count:
            offset = random.randint(0, sound_count - 1)
            return query_sounds.all()[offset]
        else:
            return None

    def get_analyzers_data_select_sql(self):
        """Returns the SQL bits to add to bulk_query and bulk_query_solr so that analyzer's data is selected
        in the bulk query"""
        analyzers_select_section_parts = []
        for analyzer_name, analyzer_info in settings.ANALYZERS_CONFIGURATION.items():
            if 'descriptors_map' in analyzer_info:
                analyzers_select_section_parts.append("{0}.analysis_data as {0},"
                                                      .format(analyzer_name.replace('-', '_')))
        return "\n          ".join(analyzers_select_section_parts)

    def get_analyzers_data_left_join_sql(self):
        """Returns the SQL bits to add to bulk_query and bulk_query_solr so that analyzer's data can be left joined
        in the bulk query"""
        analyzers_left_join_section_parts = []
        for analyzer_name, analyzer_info in settings.ANALYZERS_CONFIGURATION.items():
            if 'descriptors_map' in analyzer_info:
                analyzers_left_join_section_parts.append(
                    "LEFT JOIN sounds_soundanalysis {0} ON (sound.id = {0}.sound_id AND {0}.analyzer = '{1}')"
                        .format(analyzer_name.replace('-', '_'), analyzer_name))
        return "\n          ".join(analyzers_left_join_section_parts)

    def get_analysis_state_essentia_exists_sql(self):
        """Returns the SQL bits to add analysis_state_essentia_exists to the returned data indicating if thers is a
        SoundAnalysis objects existing for th given sound_id for the essentia analyzer and with status OK"""
        return f"          exists(select 1 from sounds_soundanalysis where sounds_soundanalysis.sound_id = sound.id AND sounds_soundanalysis.analyzer = '{settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME}' AND sounds_soundanalysis.analysis_status = 'OK') as analysis_state_essentia_exists,"

    def bulk_query_solr(self, sound_ids):
        """For each sound, get all fields needed to index the sound in Solr. Using this custom query to avoid the need
        of having to do some extra queries when displaying some fields related to the sound (e.g. for tags). Using this
        method, all the information for all requested sounds is obtained with a single query."""
        query = """SELECT
          auth_user.username,
          sound.user_id,
          sound.id,
          sound.type,
          sound.original_filename,
          sound.is_explicit,
          sound.filesize,
          sound.md5,
          sound.channels,
          sound.avg_rating,
          sound.num_ratings,
          sound.description,
          sound.created,
          sound.num_downloads,
          sound.num_comments,
          sound.duration,
          sound.pack_id,
          sound.geotag_id,
          sound.bitrate,
          sound.bitdepth,
          sound.samplerate,
          sounds_pack.name as pack_name,
          sounds_license.name as license_name,
          geotags_geotag.lat as geotag_lat,
          geotags_geotag.lon as geotag_lon,
          geotags_geotag.location_name as geotag_name,
          %s
          exists(select 1 from sounds_sound_sources where from_sound_id=sound.id) as is_remix,
          exists(select 1 from sounds_sound_sources where to_sound_id=sound.id) as was_remixed,
          ARRAY(
            SELECT tags_tag.name
            FROM tags_tag
            LEFT JOIN tags_taggeditem ON tags_taggeditem.object_id = sound.id
          WHERE tags_tag.id = tags_taggeditem.tag_id
           AND tags_taggeditem.content_type_id=%s) AS tag_array,
          ARRAY(
            SELECT comments_comment.comment
            FROM comments_comment
            WHERE comments_comment.sound_id = sound.id) AS comments_array
        FROM
          sounds_sound sound
          LEFT JOIN auth_user ON auth_user.id = sound.user_id
          LEFT JOIN sounds_pack ON sound.pack_id = sounds_pack.id
          LEFT JOIN sounds_license ON sound.license_id = sounds_license.id
          LEFT JOIN geotags_geotag ON sound.geotag_id = geotags_geotag.id
          %s
        """ % (self.get_analyzers_data_select_sql(),
               ContentType.objects.get_for_model(Sound).id,
               self.get_analyzers_data_left_join_sql())
        query += "WHERE sound.id IN %s"
        return self.raw(query, [tuple(sound_ids)])

    def bulk_query(self, where, order_by, limit, args):
        """For each sound, get all fields needed to display a sound on the web (using display_sound templatetag) or
         in the API (including AudioCommons output analysis). Using this custom query to avoid the need of having to do
         some extra queries when displaying some fields related to the sound (e.g. for tags). Using this method, all the
         information for all requested sounds is obtained with a single query."""
        query = """SELECT
          auth_user.username,
          sound.id,
          sound.type,
          sound.user_id,
          sound.original_filename,
          sound.is_explicit,
          sound.avg_rating,
          sound.channels,
          sound.filesize,
          sound.bitdepth,
          sound.bitrate,
          sound.samplerate,
          sound.num_ratings,
          sound.description,
          sound.moderation_state,
          sound.processing_state,
          sound.processing_ongoing_state,
          sound.similarity_state,
          sound.created,
          sound.num_downloads,
          sound.num_comments,
          sound.pack_id,
          sound.duration,
          sounds_pack.name as pack_name,
          sound.license_id,
          sounds_license.name as license_name,
          sounds_license.deed_url as license_deed_url,
          sound.geotag_id,
          geotags_geotag.lat as geotag_lat,
          geotags_geotag.lon as geotag_lon,
          geotags_geotag.location_name as geotag_name,
          sounds_remixgroup_sounds.id as remixgroup_id,
          accounts_profile.has_avatar as user_has_avatar,
          %s
          %s
          ARRAY(
            SELECT tags_tag.name
            FROM tags_tag
            LEFT JOIN tags_taggeditem ON tags_taggeditem.object_id = sound.id
          WHERE tags_tag.id = tags_taggeditem.tag_id
           AND tags_taggeditem.content_type_id=%s) AS tag_array
        FROM
          sounds_sound sound
          LEFT JOIN auth_user ON auth_user.id = sound.user_id
          LEFT JOIN accounts_profile ON accounts_profile.user_id = sound.user_id
          LEFT JOIN sounds_pack ON sound.pack_id = sounds_pack.id
          LEFT JOIN sounds_license ON sound.license_id = sounds_license.id
          LEFT JOIN geotags_geotag ON sound.geotag_id = geotags_geotag.id
          %s
          LEFT OUTER JOIN sounds_remixgroup_sounds ON sounds_remixgroup_sounds.sound_id = sound.id
        WHERE %s """ % (self.get_analysis_state_essentia_exists_sql(),
                        self.get_analyzers_data_select_sql(),
                        ContentType.objects.get_for_model(Sound).id,
                        self.get_analyzers_data_left_join_sql(),
                        where, )
        if order_by:
            query = f"{query} ORDER BY {order_by}"
        if limit:
            query = f"{query} LIMIT {limit}"
        return self.raw(query, args)

    def bulk_sounds_for_user(self, user_id, limit=None):
        where = """sound.moderation_state = 'OK'
            AND sound.processing_state = 'OK'
            AND sound.user_id = %s"""
        order_by = "sound.created DESC"
        if limit:
            limit = str(limit)
        return self.bulk_query(where, order_by, limit, (user_id, ))

    def bulk_sounds_for_pack(self, pack_id, limit=None):
        where = """sound.moderation_state = 'OK'
            AND sound.processing_state = 'OK'
            AND sound.pack_id = %s"""
        order_by = "sound.created DESC"
        if limit:
            limit = str(limit)
        return self.bulk_query(where, order_by, limit, (pack_id, ))

    def bulk_query_id(self, sound_ids):
        if not isinstance(sound_ids, list):
            sound_ids = [sound_ids]
        where = "sound.id = ANY(%s)"
        return self.bulk_query(where, "", "", (sound_ids, ))

    def dict_ids(self, sound_ids):
        return {sound_obj.id: sound_obj for sound_obj in self.bulk_query_id(sound_ids)}

    def ordered_ids(self, sound_ids):
        sounds = self.dict_ids(sound_ids)
        return [sounds[sound_id] for sound_id in sound_ids if sound_id in sounds]


class PublicSoundManager(models.Manager):
    """ a class which only returns public sounds """
    def get_queryset(self):
        return super().get_queryset().filter(moderation_state="OK", processing_state="OK")


class Sound(SocialModel):
    user = models.ForeignKey(User, related_name="sounds", on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    # "original_filename" is the name given to the sound, which typically is similar to the filename. note that this
    # property is named in a misleading way and should probably be renamed to "name" or "sound_name".
    original_filename = models.CharField(max_length=512)

    # "original_path" is the path on disk of the original sound file. This property is only used at upload time and
    # updated when the sound is moved from its upload location to the final destination. After that the property should
    # never be used again as Sound.locations('path') is preferred. For more clarity this property should be renamed to
    # "path" or "sound_path"
    original_path = models.CharField(max_length=512, null=True, blank=True, default=None)

    # "base_filename_slug" is a slugified version of the original filename, set at upload time. This is used
    # to create the friendly filename when downloading the sound and once set is never changed.
    base_filename_slug = models.CharField(max_length=512, null=True, blank=True, default=None)

    # user defined fields
    description = models.TextField()
    date_recorded = models.DateField(null=True, blank=True, default=None)

    # The history of licenses for a sound is stored on SoundLicenseHistory 'license' references the last one
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None, on_delete=models.SET_NULL, related_name='sounds')
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None, on_delete=models.SET_NULL)

    # fields for specifying if the sound was uploaded via API or via bulk upload process (or none)
    uploaded_with_apiv2_client = models.ForeignKey(
        ApiV2Client, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    uploaded_with_bulk_upload_progress = models.ForeignKey(
        BulkUploadProgress, null=True, blank=True, default=None, on_delete=models.SET_NULL)

    # file properties
    SOUND_TYPE_CHOICES = (
        ('wav', 'Wave'),
        ('ogg', 'Ogg Vorbis'),
        ('aiff', 'AIFF'),
        ('mp3', 'Mp3'),
        ('flac', 'Flac'),
        ('m4a', 'M4a')
    )
    type = models.CharField(db_index=True, max_length=4, choices=SOUND_TYPE_CHOICES)
    duration = models.FloatField(default=0)
    bitrate = models.IntegerField(default=0)
    bitdepth = models.IntegerField(null=True, blank=True, default=None)
    samplerate = models.FloatField(default=0)
    filesize = models.IntegerField(default=0)
    channels = models.IntegerField(default=0)
    md5 = models.CharField(max_length=32, unique=True, db_index=True)
    crc = models.CharField(max_length=8, blank=True)

    # moderation and index
    MODERATION_STATE_CHOICES = (
        ("PE", 'Pending'),
        ("OK", 'OK'),
        ("DE", 'Deferred'),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)  # Set at last moderation state change
    moderation_note = models.TextField(null=True, blank=True, default=None)
    has_bad_description = models.BooleanField(default=False)
    is_explicit = models.BooleanField(default=False)

    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE", 'Pending'),  # Sounds will only be in "PE" before the very first time they are processed
        ("OK", 'OK'),
        ("FA", 'Failed'),
    )
    PROCESSING_ONGOING_STATE_CHOICES = (
        ("NO", 'None'),
        ("QU", 'Queued'),
        ("PR", 'Processing'),
        ("FI", 'Finished'),
    )
    ANALYSIS_STATE_CHOICES = PROCESSING_STATE_CHOICES + (("SK", 'Skipped'), ("QU", 'Queued'),)
    SIMILARITY_STATE_CHOICES = PROCESSING_STATE_CHOICES

    processing_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")
    processing_ongoing_state = models.CharField(db_index=True, max_length=2,
                                                choices=PROCESSING_ONGOING_STATE_CHOICES, default="NO")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)  # Set at last processing attempt
    processing_log = models.TextField(null=True, blank=True, default=None)

    # state
    is_index_dirty = models.BooleanField(null=False, default=True)
    similarity_state = models.CharField(db_index=True, max_length=2, choices=SIMILARITY_STATE_CHOICES, default="PE")
    analysis_state = models.CharField(db_index=True, max_length=2, choices=ANALYSIS_STATE_CHOICES, default="PE")  # This field is no longer used and should be removed

    # counts, updated by django signals
    num_comments = models.PositiveIntegerField(default=0)
    num_downloads = models.PositiveIntegerField(default=0, db_index=True)
    avg_rating = models.FloatField(default=0)  # Store average rating from 0 to 10
    num_ratings = models.PositiveIntegerField(default=0)

    objects = SoundManager()
    public = PublicSoundManager()

    def __str__(self):
        return self.base_filename_slug

    @staticmethod
    def is_sound():
        # N.B. This is used in the ticket template (ugly, but a quick fix)
        return True

    def friendly_filename(self):
        filename_slug = slugify(os.path.splitext(self.original_filename)[0])
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.%s" % (self.id, username_slug, filename_slug, self.type)

    @locations_decorator()
    def locations(self):
        id_folder = str(old_div(self.id,1000))
        sound_user_id = self.user_id
        previews_url = settings.PREVIEWS_URL if not settings.USE_CDN_FOR_PREVIEWS else settings.CDN_PREVIEWS_URL
        displays_url = settings.DISPLAYS_URL if not settings.USE_CDN_FOR_DISPLAYS else settings.CDN_DISPLAYS_URL
        return dict(
            path=os.path.join(settings.SOUNDS_PATH, id_folder, "%d_%d.%s" % (self.id, sound_user_id, self.type)),
            sendfile_url=settings.SOUNDS_SENDFILE_URL + "%s/%d_%d.%s" % (id_folder, self.id, sound_user_id, self.type),
            preview=dict(
                HQ=dict(
                    mp3=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-hq.mp3" % (self.id, sound_user_id)),
                        url=previews_url + "%s/%d_%d-hq.mp3" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-hq.mp3" % (self.id, sound_user_id),
                    ),
                    ogg=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-hq.ogg" % (self.id, sound_user_id)),
                        url=previews_url + "%s/%d_%d-hq.ogg" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-hq.ogg" % (self.id, sound_user_id),
                    )
                ),
                LQ=dict(
                    mp3=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-lq.mp3" % (self.id, sound_user_id)),
                        url=previews_url + "%s/%d_%d-lq.mp3" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-lq.mp3" % (self.id, sound_user_id),
                    ),
                    ogg=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-lq.ogg" % (self.id, sound_user_id)),
                        url=previews_url + "%s/%d_%d-lq.ogg" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-lq.ogg" % (self.id, sound_user_id),
                    ),
                )
            ),
            display=dict(
                spectral=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_M.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_spec_M.jpg" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_L.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_spec_L.jpg" % (id_folder, self.id, sound_user_id)
                    )
                ),
                wave=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_M.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_wave_M.png" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_L.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_wave_L.png" % (id_folder, self.id, sound_user_id)
                    )
                ),
                spectral_bw=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_bw_M.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_spec_bw_M.jpg" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_bw_L.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_spec_bw_L.jpg" % (id_folder, self.id, sound_user_id)
                    )
                ),
                wave_bw=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_bw_M.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_wave_bw_M.png" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_bw_L.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=displays_url + "%s/%d_%d_wave_bw_L.png" % (id_folder, self.id, sound_user_id)
                    )
                )
            ),
            analysis=dict(
                base_path=os.path.join(settings.ANALYSIS_PATH, id_folder),
                statistics=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d-%s.yaml" % (
                        self.id, settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME)),
                    url=settings.ANALYSIS_URL + "%s/%d-%s.yaml" % (
                        id_folder, self.id, settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME)
                ),
                frames=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d-%s_frames.json" % (
                        self.id, settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME)),
                    url=settings.ANALYSIS_URL + "%s/%d-%s_frames.json" % (
                        id_folder, self.id, settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME)
                )
            )
        )

    def get_preview_abs_url(self):
        preview_url = self.locations()['preview']['LQ']['mp3']['url']
        if (preview_url.startswith('http')):
            # If we're serving previews from a CDN, then the URL returned from locations will already include the full URL
            return preview_url
        return f'https://{Site.objects.get_current().domain}{preview_url}'

    def get_thumbnail_abs_url(self, size='M'):
        thumbnail_url = self.locations()['display']['wave'][size]['url']
        if (thumbnail_url.startswith('http')):
            # If we're serving previews from a CDN, then the URL returned from locations will already include the full URL
            return thumbnail_url
        return f'https://{Site.objects.get_current().domain}{thumbnail_url}'

    def get_large_thumbnail_abs_url(self):
        return self.get_thumbnail_abs_url(size='L')

    def get_channels_display(self):
        if self.channels == 1:
            return "Mono"
        elif self.channels == 2:
            return "Stereo"
        else:
            return self.channels

    def type_warning(self):
        return self.type == "ogg" or self.type == "flac"

    def duration_warning(self):
        # warn from 5 minutes and more
        return self.duration > 60*5

    def filesize_warning(self):
        # warn for 50MB and up
        return self.filesize > 50 * 1024 * 1024

    def samplerate_warning(self):
        # warn anything special
        return self.samplerate not in [11025, 22050, 44100]

    def bitdepth_warning(self):
        return self.bitdepth not in [8, 16]

    def bitrate_warning(self):
        return self.bitrate not in settings.COMMON_BITRATES

    def channels_warning(self):
        return self.channels not in [1, 2]

    def duration_ms(self):
        return self.duration * 1000

    def rating_percent(self):
        if self.num_ratings < settings.MIN_NUMBER_RATINGS:
            return 0
        return int(self.avg_rating*10)

    @property
    def avg_rating_0_5(self):
        # Returns the average raring, normalized from 0 tp 5
        return old_div(self.avg_rating, 2)

    def get_absolute_url(self):
        return reverse('sound', args=[self.user.username, smart_text(self.id)])

    @property
    def license_bw_icon_name(self):
        license_name = self.license.name
        if '0' in license_name.lower():
            return 'zero'
        elif 'noncommercial' in license_name.lower():
            return 'nc'
        elif 'attribution' in license_name.lower():
            return 'by'
        return 'cc'

    def get_license_history(self):
        """
        Returns a list of tuples with the following format:
            (license_name, timestamp)
        License name is a string, while timestamps are represented as python datetime objects.
        The list represent the different licenses that have been assigned to a single sound.
        If a sound never had a license changed, then the list will have a single element.
        List is sorted with the newest license at the top.
        """
        return [(slh.created, slh.license) for slh in
                self.soundlicensehistory_set.select_related('license').order_by('-created')]

    def get_sound_tags(self, limit=None):
        """
        Returns the tags assigned to the sound as a list of strings, e.g. ["tag1", "tag2", "tag3"]
        :param limit: The maximum number of tags to return
        """
        return [ti.tag.name for ti in self.tags.select_related("tag").all().order_by('tag__name')[0:limit]]

    def get_sound_tags_string(self, limit=None):
        """
        Returns the tags assigned to the sound as a string with tags separated by spaces, e.g. "tag1 tag2 tag3"
        :param limit: The maximum number of tags to return
        """
        return " ".join(self.get_sound_tags(limit=limit))

    def set_tags(self, tags):
        """
        Updates the tags of the Sound object. To do that it first removes all TaggedItem objects which relate the sound
        with tags which are not in the provided list of tags, and then adds the new tags.
        :param list tags: list of strings representing the new tags that the Sound object should be assigned
        """
        # remove tags that are not in the list
        for tagged_item in self.tags.all():
            if tagged_item.tag.name not in tags:
                tagged_item.delete()

        # add tags that are not there yet
        for tag in tags:
            if self.tags.filter(tag__name=tag).count() == 0:
                (tag_object, created) = Tag.objects.get_or_create(name=tag)
                tagged_object = TaggedItem.objects.create(user=self.user, tag=tag_object, content_object=self)
                tagged_object.save()

    def set_license(self, new_license):
        """
        Set `new_license` as the current license of the sound. Create the corresponding SoundLicenseHistory object.
        Note that this method *does not save* the sound object, it needs to be manually done afterwards.
        :param License new_license: License object representing the new license
        """
        self.license = new_license
        SoundLicenseHistory.objects.create(sound=self, license=new_license)

    def get_sound_sources_as_set(self):
        """
        Returns a set object with the integer sound IDs of the current sources of the sound
        """
        return {source["id"] for source in self.sources.all().values("id")}

    def set_sources(self, new_sources):
        """
        :param set new_sources: set object with the integer IDs of the sounds which should be set as sources of the sound
        """
        new_sources.discard(self.id)  # stop the universe from collapsing :-D
        old_sources = self.get_sound_sources_as_set()
        
        # process sources in old but not in new
        for sid in old_sources - new_sources:
            try:
                source = Sound.objects.get(id=sid)
                self.sources.remove(source)
                source.invalidate_template_caches()
            except Sound.DoesNotExist:
                pass

        # process sources in new but not in old
        for sid in new_sources - old_sources:
            source = Sound.objects.get(id=sid)
            source.invalidate_template_caches()
            self.sources.add(source)
            send_mail_template(
                settings.EMAIL_SUBJECT_SOUND_ADDED_AS_REMIX, 'sounds/email_remix_update.txt',
                {'source': source, 'action': 'added', 'remix': self},
                user_to=source.user, email_type_preference_check='new_remix')
        
        if old_sources != new_sources:
            self.invalidate_template_caches()

    # N.B. The set_xxx functions below are used in the distributed processing and other parts of the app where we only
    # want to save an individual field of the model to prevent overwritting other model fields.

    def set_processing_ongoing_state(self, state):
        """
        Updates self.processing_ongoing_state field of the Sound object and saves to DB without updating other
        fields. This function is used in cases when two instances of the same Sound object could be edited by
        two processes in parallel and we want to avoid possible field overwrites.
        :param str state: new state to which self.processing_ongoing_state should be set
        """
        self.processing_ongoing_state = state
        self.save(update_fields=['processing_ongoing_state'])

    def set_similarity_state(self, state):
        """
        Updates self.similarity_state field of the Sound object and saves to DB without updating other
        fields. This function is used in cases when two instances of the same Sound object could be edited by
        two processes in parallel and we want to avoid possible field overwrites.
        :param str state: new state to which self.similarity_state should be set
        """
        self.similarity_state = state
        self.save(update_fields=['similarity_state'])

    def set_audio_info_fields(self, samplerate=None, bitrate=None, bitdepth=None, channels=None, duration=None):
        """
        Updates several fields of the Sound object which store some audio properties and saves to DB without
        updating other fields. This function is used in cases when two instances of the same Sound object could be
        edited by two processes in parallel and we want to avoid possible field overwrites.
        :param int samplerate: saplerate to store
        :param int bitrate: bitrate to store
        :param int bitdepth: bitdepth to store
        :param int channels: number of channels to store
        :param float duration: duration to store
        """
        update_fields = []
        if samplerate is not None:
            self.samplerate = samplerate
            update_fields.append('samplerate')
        if bitrate is not None:
            self.bitrate = bitrate
            update_fields.append('bitrate')
        if bitdepth is not None:
            self.bitdepth = bitdepth
            update_fields.append('bitdepth')
        if channels is not None:
            self.channels = channels
            update_fields.append('channels')
        if duration is not None:
            self.duration = duration
            update_fields.append('duration')
        self.save(update_fields=update_fields)

    def change_moderation_state(self, new_state):
        """
        Change the moderation state of a sound and perform related tasks such as marking the sound as index dirty
        or sending a pack to process if required.
        :param str new_state: new moderation state to which the sound should be set
        """
        current_state = self.moderation_state
        if current_state != new_state:
            self.mark_index_dirty(commit=False)
            self.moderation_state = new_state
            self.moderation_date = datetime.datetime.now()
            self.save()

            if new_state != 'OK':
                # If the moderation state changed and now the sound is not moderated OK, delete it from indexes
                self.delete_from_indexes()

            if (current_state == 'OK' and new_state != 'OK') or (current_state != 'OK' and new_state == 'OK'):
                # Sound either passed from being approved to not being approved, or from not being approved to
                # being approved. In that case we need to update num_sounds counts of sound's author and pack (if any)
                self.user.profile.update_num_sounds()
                if self.pack:
                    self.pack.process()
        else:
            # If the moderation state has not changed, only update moderation date
            self.moderation_date = datetime.datetime.now()
            self.save()

        self.invalidate_template_caches()

    def change_processing_state(self, new_state, processing_log=None):
        """
        Change the processing state of a sound and perform related tasks such as set the sound as index dirty if
        required. Only the fields that are changed are saved to the object. This is needed when the processing tasks
        change the processing state of the sound to avoid potential collisions when saving the whole object.
        :param str new_state: new processing state to which the sound should be set
        :param str processing_log: processing log to be saved in the Sound object
        """
        current_state = self.processing_state
        if current_state != new_state:
            # Sound either went from PE to OK, from PE to FA, from OK to FA, or from FA to OK (never from OK/FA to PE)
            self.mark_index_dirty(commit=False)
            self.processing_state = new_state
            self.processing_date = datetime.datetime.now()
            if self.processing_log is None:
                self.processing_log = ''
            self.processing_log += f'----Processed sound {datetime.datetime.today()} - {self.id}\n{processing_log}'
            self.save(update_fields=['processing_state', 'processing_date', 'processing_log', 'is_index_dirty'])

            if new_state == 'FA':
                # Sound became processing failed, delete it from indexes
                self.delete_from_indexes()

            # Update num_sounds counts of sound's author and pack (if any)
            self.user.profile.update_num_sounds()
            if self.pack:
                self.pack.process()

        else:
            # If processing state has not changed, only update the processing date and log
            self.processing_date = datetime.datetime.now()
            if self.processing_log is None:
                self.processing_log = ''
            self.processing_log += f'----Processed sound {datetime.datetime.today()} - {self.id}\n{processing_log}'
            self.save(update_fields=['processing_date', 'processing_log'])

        self.invalidate_template_caches()

    def change_owner(self, new_owner):
        """
        Change the owner (i.e. author) of a Sound object by assigning a new User object to the user field.
        If sound is part of a Pack, when changing the owner a new Pack object is created for the new owner.
        Changing the owner of the sound also includes renaming and moving all associated files (i.e. sound, previews,
        displays and analysis) to include the ID of the new owner and be located accordingly.
        NOTE: see comments in https://github.com/MTG/freesound/issues/750 for more information
        :param User new_owner: User object of the new sound owner
        """

        def replace_user_id_in_path(path, old_owner_id, new_owner_id):
            old_path_beginning = '%i_%i' % (self.id, old_owner_id)
            new_path_beginning = '%i_%i' % (self.id, new_owner_id)
            return path.replace(old_path_beginning, new_path_beginning)

        # Rename related files in disk
        paths_to_rename = [
            self.locations('path'),  # original file path
            self.locations('analysis.frames.path'),  # analysis frames file
            self.locations('analysis.statistics.path'),  # analysis statistics file
            self.locations('display.spectral.L.path'),  # spectrogram L
            self.locations('display.spectral.M.path'),  # spectrogram M
            self.locations('display.wave_bw.L.path'),  # waveform BW L
            self.locations('display.wave_bw.M.path'),  # waveform BW M
            self.locations('display.spectral_bw.L.path'),  # spectrogram BW L
            self.locations('display.spectral_bw.M.path'),  # spectrogram BW M
            self.locations('display.wave.L.path'),  # waveform L
            self.locations('display.wave.M.path'),  # waveform M
            self.locations('preview.HQ.mp3.path'),  # preview HQ mp3
            self.locations('preview.HQ.ogg.path'),  # preview HQ ogg
            self.locations('preview.LQ.mp3.path'),  # preview LQ mp3
            self.locations('preview.LQ.ogg.path'),  # preview LQ ogg
        ]
        for path in paths_to_rename:
            try:
                os.rename(path, replace_user_id_in_path(path, self.user.id, new_owner.id))
            except OSError:
                web_logger.error('WARNING changing owner of sound %i: Could not rename file %s because '
                                 'it does not exist.\n' % (self.id, path))

        # Deal with pack
        # If sound is in pack, replicate pack in new user.
        # If pack already exists in new user, add sound to that existing pack.
        old_pack = None
        if self.pack:
            old_pack = self.pack
            (new_pack, created) = Pack.objects.get_or_create(user=new_owner, name=self.pack.name)
            self.pack = new_pack

        # Change tags ownership too (otherwise they might get deleted if original user is deleted)
        self.tags.all().update(user=new_owner)

        # Change user field
        old_owner = self.user
        self.user = new_owner

        # Change original_path field
        self.original_path = replace_user_id_in_path(self.original_path, old_owner.id, new_owner.id)

        # Set index dirty
        self.mark_index_dirty(commit=True)  # commit=True does save

        # Update old owner and new owner profiles
        old_owner.profile.update_num_sounds()
        new_owner.profile.update_num_sounds()

        # Process old and new packs
        if old_pack:
            old_pack.process()
            new_pack.process()

        # NOTE: see comments in https://github.com/MTG/freesound/issues/750

    def mark_index_dirty(self, commit=True):
        self.is_index_dirty = True
        if commit:
            self.save()

    def add_comment(self, user, comment):
        comment = Comment(sound=self, user=user, comment=comment)
        comment.save()
        self.num_comments = F('num_comments') + 1
        self.mark_index_dirty(commit=False)
        self.save()

    def post_delete_comment(self, commit=True):
        """ When a comment is deleted this method is called to update num_comments """
        self.num_comments = F('num_comments') - 1
        self.mark_index_dirty(commit=False)
        if commit:
            self.save()

    def compute_crc(self, commit=True):
        crc = 0
        sound_path = self.locations('path')
        if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
            sound_path = self.locations("preview.LQ.mp3.path")

        with open(sound_path, 'rb') as fp:
            for data in iter(lambda: fp.read(settings.CRC_BUFFER_SIZE), b''):
                crc = zlib.crc32(data, crc)

        self.crc = f'{crc & 0xffffffff:0>8x}'  # right aligned with zero-padding, width of 8 chars

        if commit:
            self.save()

    def create_moderation_ticket(self):
        ticket = Ticket.objects.create(
            title=f'Moderate sound {self.original_filename}',
            status=TICKET_STATUS_NEW,
            queue=Queue.objects.get(name='sound moderation'),
            sender=self.user,
            sound=self,
        )
        TicketComment.objects.create(
            sender=self.user,
            text=f"I've uploaded {self.original_filename}. Please moderate!",
            ticket=ticket,
        )

    def unlink_moderation_ticket(self):
        # If sound has an assigned ticket, set its content to None and status to closed
        try:
            ticket = self.ticket
            ticket.status = TICKET_STATUS_CLOSED
            ticket.sound = None
            ticket.save()
        except Ticket.DoesNotExist:
            pass

    def process_and_analyze(self, force=False, high_priority=False):
        """
        Process and analyze a sound if the sound has a processing state different than "OK" and/or and analysis state
        other than "OK". 'force' argument can be used to trigger processing and analysis regardless of the processing
        state and analysis state of the sound.
        NOTE: high_priority is not implemented and setting it has no effect
        """
        self.process(force=force, high_priority=high_priority)
        self.analyze(force=force, high_priority=high_priority)

    def process(self, force=False, skip_previews=False, skip_displays=False, high_priority=False):
        """
        Trigger processing of the sound if processing_state is not "OK" or force=True.
        'skip_previews' and 'skip_displays' arguments can be used to disable the computation of either of these steps.
        Processing code generates the file previews and display images as well as fills some audio fields
        of the Sound model. This method returns "True" if sound was sent to process, None otherwise.
        NOTE: high_priority is not implemented and setting it has no effect
        """
        if force or ((self.processing_state != "OK" or self.processing_ongoing_state != "FI") and self.estimate_num_processing_attemps() <= 3):
            self.set_processing_ongoing_state("QU")
            tasks.process_sound.delay(sound_id=self.id, skip_previews=skip_previews, skip_displays=skip_displays)
            sounds_logger.info(f"Send sound with id {self.id} to queue 'process'")
            return True

    def estimate_num_processing_attemps(self):
        # Estimates how many processing attemps have been made by looking at the processing logs 
        if self.processing_log is not None:
            return max(1, self.processing_log.count('----Processed sound'))
        else:
            return 0

    def analyze(self, analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, force=False, verbose=True, high_priority=False):
        # Note that "high_priority" is not implemented but needs to be here for compatibility with older code
        if analyzer not in settings.ANALYZERS_CONFIGURATION.keys():
            # If specified analyzer is not one of the analyzers configured, do nothing
            if verbose:
                sounds_logger.info(f"Not sending sound {self.id} to unknown analyzer {analyzer}")
            return None

        sa, created = SoundAnalysis.objects.get_or_create(sound=self, analyzer=analyzer)
        if not sa.analysis_status == "QU" or force or created:
            # Only send to queue if not already in queue
            sa.num_analysis_attempts += 1
            sa.analysis_status = "QU"
            sa.analysis_time = 0
            sa.last_sent_to_queue = datetime.datetime.now()
            sa.save(update_fields=['num_analysis_attempts', 'analysis_status', 'last_sent_to_queue', 'analysis_time'])
            sound_path = self.locations('path')
            if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
                sound_path = self.locations("preview.LQ.mp3.path")
            celery_app.send_task(analyzer, kwargs={'sound_id': self.id, 'sound_path': sound_path,
                        'analysis_folder': self.locations('analysis.base_path'), 'metadata':json.dumps({'duration': self.duration})}, queue=analyzer)
            if verbose:
                sounds_logger.info(f"Sending sound {self.id} to analyzer {analyzer}")
        else:
            if verbose:
                sounds_logger.info(f"Not sending sound {self.id} to analyzer {analyzer} as is already queued")
        return sa

    def delete_from_indexes(self):
        delete_sounds_from_search_engine([self.id])
        delete_sound_from_gaia(self.id)

    def invalidate_template_caches(self):
        for is_explicit in [True, False]:
            invalidate_template_cache("sound_header", self.id, is_explicit)

        for display_random_link in [True, False]:
            invalidate_template_cache("sound_footer_top", self.id, display_random_link)

        invalidate_template_cache("sound_footer_bottom", self.id)

        for is_authenticated in [True, False]:
            for is_explicit in [True, False]:
                invalidate_template_cache("display_sound", self.id, is_authenticated, is_explicit)
                for player_size in ['small', 'middle', 'big_no_info', 'small_no_info', 'minimal', 'infowindow']:
                    invalidate_template_cache("bw_display_sound", self.id, is_authenticated, is_explicit, player_size)

        invalidate_template_cache("bw_sound_page", self.id)
        invalidate_template_cache("bw_sound_page_sidebar", self.id)

    def get_geotag_name(self):
        if settings.USE_TEXTUAL_LOCATION_NAMES_IN_BW:
            if hasattr(self, 'geotag_name'):
                name = self.geotag_name
            else:
                name = self.geotag.location_name
            if name:
                return name
        if hasattr(self, 'geotag_lat'):
            return f'{self.geotag_lat:.3f}, {self.geotag_lon:.3f}'
        else:
            return f'{self.geotag.lat:.3f}, {self.geotag.lon:.3f}'


    class Meta(SocialModel.Meta):
        ordering = ("-created", )


class SoundOfTheDayManager(models.Manager):
    def create_sound_for_date(self, date_display):
        """Create a random sound of the day for a specific date.
        Make sure that the sound hasn't already been chosen as a sound of the day
        and that it is not by a user who has recently had their sound chosen.

        Returns:
            True if the sound was created
            False if no sound of the day was able to be created (e.g. if there are no sounds available)
        """
        already_created = self.model.objects.filter(date_display=date_display).exists()
        if already_created:
            return True

        days_for_user = settings.NUMBER_OF_DAYS_FOR_USER_RANDOM_SOUNDS
        date_from = date_display - datetime.timedelta(days=days_for_user)
        users = self.model.objects.filter(
                date_display__lt=date_display,
                date_display__gte=date_from).distinct().values_list('sound__user_id', flat=True)
        used_sounds = self.model.objects.values_list('sound_id', flat=True)

        sound = Sound.objects.random(excludes={'user__id__in': users, 'id__in': used_sounds})
        if sound:
            rnd = self.model.objects.create(sound=sound, date_display=date_display)
        else:
            return False

        return True

    def get_sound_for_date(self, date_display):
        """Get a sound that has been chosen for a given date

        Returns:
            A sound for the given date
        Raises:
            SoundOfTheDay.DoesNotExist if no sound of the day for this date has been created
        """
        return self.model.objects.get(date_display=date_display)


class SoundOfTheDay(models.Model):
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    date_display = models.DateField(db_index=True)
    email_sent = models.BooleanField(default=False)

    objects = SoundOfTheDayManager()

    def __str__(self):
        return f'Random sound of the day {self.date_display}'

    def notify_by_email(self):
        """Notify the user of this sound by email that their sound has been chosen
        as our Sound of the Day.
        If the email has already been sent, don't send the notification.
        If the user has disabled the email notifications for this type of message, don't send it.

        Returns:
            True if the email was sent
            False if it was not sent
        """
        sounds_logger.info("Notifying user of random sound of the day")
        if self.email_sent:
            sounds_logger.info("Email was already sent")
            return False

        send_mail_template(
            settings.EMAIL_SUBJECT_RANDOM_SOUND_OF_THE_SAY_CHOOSEN, 'sounds/email_random_sound.txt',
            {'sound': self.sound, 'user': self.sound.user},
            user_to=self.sound.user, email_type_preference_check="random_sound")
        self.email_sent = True
        self.save()

        sounds_logger.info("Finished sending mail to user %s of random sound of the day %s" %
                          (self.sound.user, self.sound))

        return True


class DeletedSound(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    sound_id = models.IntegerField(default=0, db_index=True)
    data = JSONField()


def on_delete_sound(sender, instance, **kwargs):

    ds, create = DeletedSound.objects.get_or_create(
        sound_id=instance.id,
        defaults={'data': {}})
    ds.user = instance.user

    # Copy relevant data to DeletedSound for future research
    # Note: we do not store information about individual downloads and ratings, we only
    # store count and average (for ratings). We do not store at all information about bookmarks.

    try:
        data = list(Sound.objects.filter(pk=instance.pk).values())[0]
    except IndexError:
        # The sound being deleted can't be found on the database. This might happen if a sound is being deleted
        # multiple times concurrently, and in one "thread" the sound object has already been deleted when reaching
        # this part of the code. If that happens, return form this function without creating the DeletedSound
        # object nor doing any of the other steps as this will have been already carried out.
        return

    username = None
    if instance.user:
        username = instance.user.username
    data['username'] = username

    pack = None
    if instance.pack:
        pack = list(Pack.objects.filter(pk=instance.pack.pk).values())[0]
    data['pack'] = pack

    geotag = None
    if instance.geotag:
        geotag = list(GeoTag.objects.filter(pk=instance.geotag.pk).values())[0]
    data['geotag'] = geotag

    license = None
    if instance.license:
        license = list(License.objects.filter(pk=instance.license.pk).values())[0]
    data['license'] = license

    data['comments'] = list(instance.comments.values())
    data['tags'] = list(instance.tags.values())
    data['sources'] = list(instance.sources.values('id'))

    # Alter datetime objects in data to avoid serialization problems
    data['created'] = str(data['created'])
    data['moderation_date'] = str(data['moderation_date'])
    data['processing_date'] = str(data['processing_date'])
    data['date_recorded'] = str(data['date_recorded'])  # This field is not used
    if instance.pack:
        data['pack']['created'] = str(data['pack']['created'])
        data['pack']['last_updated'] = str(data['pack']['last_updated'])
    for tag in data['tags']:
        tag['created'] = str(tag['created'])
    for comment in data['comments']:
        comment['created'] = str(comment['created'])
    if instance.geotag:
        geotag['created'] = str(geotag['created'])
    ds.data = data
    ds.save()

    try:
        if instance.geotag:
            instance.geotag.delete()
    except:
        pass

    instance.delete_from_indexes()
    instance.unlink_moderation_ticket()


def post_delete_sound(sender, instance, **kwargs):
    # after deleted sound update num_sounds on profile and pack
    try:
        # before updating the number of sounds here, we need to refresh the object from the DB because another signal
        # triggered after a sound is deleted (the post_delete signal on Download object) also needs to modify the
        # user profile and if we don't refresh here the changes by that other signal will be overwritten when saving
        instance.user.profile.refresh_from_db()
        instance.user.profile.update_num_sounds()
    except ObjectDoesNotExist:
        # If this is triggered after user.delete() (instead of sound.delete() or user.profile.delete_user()),
        # user object will have no profile
        pass
    if instance.pack:
        instance.pack.process()
    web_logger.info("Deleted sound with id %i" % instance.id)


pre_delete.connect(on_delete_sound, sender=Sound)
post_delete.connect(post_delete_sound, sender=Sound)


class PackManager(models.Manager):

    def ordered_ids(self, pack_ids):
        """
        Returns a list of Pack objects with ID in pack_ids and in the same order. pack_ids can include ID duplicates
        and the returned list will also include duplicated Pack objects.

        Args:
            pack_ids (List[int]): list with the IDs of the packs to be included in the output

        Returns:
            List[Pack]: List of Pack objects

        """
        packs = {pack_obj.id: pack_obj for pack_obj in Pack.objects.filter(id__in=pack_ids).exclude(is_deleted=True)}
        return [packs[pack_id] for pack_id in pack_ids if pack_id in packs]


class Pack(SocialModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default=None)
    is_dirty = models.BooleanField(db_index=True, default=False)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    license_crc = models.CharField(max_length=8, blank=True)
    last_updated = models.DateTimeField(db_index=True, auto_now_add=True)
    num_downloads = models.PositiveIntegerField(default=0)  # Updated via db trigger
    num_sounds = models.PositiveIntegerField(default=0)  # Updated via django Pack.process() method
    is_deleted = models.BooleanField(db_index=True, default=False)

    VARIOUS_LICENSES_NAME = 'Various licenses'

    objects = PackManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('pack', args=[self.user.username, smart_text(self.id)])

    class Meta(SocialModel.Meta):
        unique_together = ('user', 'name', 'is_deleted')
        ordering = ("-created",)

    def friendly_filename(self):
        name_slug = slugify(self.name)
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.zip" % (self.id, username_slug, name_slug)

    def process(self):
        sounds = self.sounds.filter(processing_state="OK", moderation_state="OK").order_by("-created")
        self.num_sounds = sounds.count()
        if self.num_sounds:
            self.last_updated = sounds[0].created
        self.save()

    def get_random_sounds_from_pack(self, N=3):
        """
        Get N random sounds from this pack. If Pack has less than N sounds, then less than N sounds will be returned.

        Args:
            N (int): maximum number of random sounds to get

        Returns:
            List[Sound]: List of randomly selected Sound objects from the pack
        """
        sound_ids = list(Sound.public.filter(pack=self.id).order_by('?').values_list('id', flat=True)[:N])
        return Sound.objects.ordered_ids(sound_ids=sound_ids)

    def get_pack_tags(self):
        try:
            pack_tags_counts = get_search_engine().get_pack_tags(self.user.username, self.name)
            tags = [tag for tag, count in pack_tags_counts]
            return {'tags': tags, 'num_tags': len(tags)}
        except SearchEngineException as e:
            return False
        except Exception as e:
            return False

    def get_pack_tags_bw(self):
        try:
            pack_tags_counts = get_search_engine().get_pack_tags(self.user.username, self.name)
            return [{'name': tag, 'count': count, 'browse_url': reverse('tags', args=[tag])}
                    for tag, count in pack_tags_counts]
        except SearchEngineException as e:
            return []
        except Exception as e:
            return []

    def remove_sounds_from_pack(self):
        Sound.objects.filter(pack_id=self.id).update(pack=None)
        self.process()

    def delete_pack(self, remove_sounds=True):
        # Pack.delete() should never be called as it will completely erase the object from the db
        # Instead, Pack.delete_pack() should be used
        if remove_sounds:
            for sound in self.sounds.all():
                sound.delete()  # Create DeletedSound objects and delete original objects
        else:
            self.sounds.update(pack=None)
        self.is_deleted = True
        self.save()

    def get_attribution(self):
        sounds_list = self.sounds.filter(processing_state="OK",
                moderation_state="OK").select_related('user', 'license')

        users = User.objects.filter(sounds__in=sounds_list).distinct()
        # Generate text file with license info
        licenses = License.objects.filter(sound__pack=self).distinct()
        attribution = render_to_string("sounds/pack_attribution.txt",
            dict(users=users,
                pack=self,
                licenses=licenses,
                sound_list=sounds_list))
        return attribution

    @property
    def avg_rating(self):
        # Return average rating from 0 to 10
        # TODO: don't compute this realtime, store it in DB
        ratings = list(SoundRating.objects.filter(sound__pack=self).values_list('rating', flat=True))
        if ratings:
            return old_div(1.0*sum(ratings),len(ratings))
        else:
            return 0

    @property
    def avg_rating_0_5(self):
        # Returns the average raring, normalized from 0 tp 5
        return old_div(self.avg_rating,2)

    @property
    def num_ratings(self):
        # TODO: store this as pack field instead of computing it live
        return SoundRating.objects.filter(sound__pack=self).count()

    def get_total_pack_sounds_length(self):
        # TODO: don't compute this realtime, store it in DB
        durations = list(Sound.objects.filter(pack=self).values_list('duration', flat=True))
        return sum(durations)

    @cached_property
    def licenses_data(self):
        licenses_data = list(Sound.objects.select_related('license').filter(pack=self).values_list('license__name', 'license_id'))
        license_ids = [lid for _, lid in licenses_data]
        license_names = [lname for lname, _ in licenses_data]
        return license_ids, license_names
    
    @property
    def license_summary_name_and_id(self):
        # TODO: store this in DB?
        license_ids, license_names = self.licenses_data
        
        if len(set(license_ids)) == 1:
            # All sounds have same license
            license_summary_name = license_names[0]
            license_id = license_ids[0]
        else:
            license_summary_name = self.VARIOUS_LICENSES_NAME
            license_id = None
        return license_summary_name, license_id

    @property
    def license_bw_icon_name(self):
        license_summary_name, _ = self.license_summary_name_and_id
        if '0' in license_summary_name.lower():
            return 'zero'
        elif 'noncommercial' in license_summary_name.lower():
            return 'nc'
        elif 'attribution' in license_summary_name.lower():
            return 'by'
        return 'cc'

    @property
    def license_summary_text(self):
        # TODO: store this in DB?
        license_summary_name, license_summary_id = self.license_summary_name_and_id
        if license_summary_name != self.VARIOUS_LICENSES_NAME:
            return License.objects.get(id=license_summary_id).get_short_summary
        else:
            return "This pack contains sounds released under various licenses. Please check every individual sound page " \
                   "(or the <i>readme</i> file upon downloading the pack) to know under which " \
                   "license each sound is released."

    @property
    def license_summary_deed_url(self):
        license_summary_name, license_summary_id = self.license_summary_name_and_id
        if license_summary_name != self.VARIOUS_LICENSES_NAME:
            return License.objects.get(id=license_summary_id).deed_url
        else:
            return ""

    @property
    def has_geotags(self):
        # Returns whether or not the pack has geotags
        # This is used in the pack page to decide whether or not to show the geotags map. Doing this generates one
        # extra DB query, but avoid doing unnecessary map loads and a request to get all geotags by a pack (which would
        # return empty query set if no geotags and indeed generate more queries).
        return Sound.objects.filter(pack=self).exclude(geotag=None).count() > 0


class Flag(models.Model):
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None, on_delete=models.CASCADE)
    email = models.EmailField()
    REASON_TYPE_CHOICES = (
        ("O", 'Offending sound'),
        ("I", 'Illegal sound'),
        ("T", 'Other problem'),
    )
    reason_type = models.CharField(max_length=1, choices=REASON_TYPE_CHOICES, default="I")
    reason = models.TextField()
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return f"{self.reason_type}: {self.reason[:100]}"

    class Meta:
        ordering = ("-created",)


class Download(models.Model):
    user = models.ForeignKey(User, related_name='sound_downloads', on_delete=models.CASCADE)
    sound = models.ForeignKey(Sound, related_name='downloads', on_delete=models.CASCADE)
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)
        indexes = [
            models.Index(fields=['user', 'sound']),
        ]


@receiver(post_delete, sender=Download)
def update_num_downloads_on_delete(**kwargs):
    download = kwargs['instance']
    if download.sound_id:
        Sound.objects.filter(id=download.sound_id).update(
            is_index_dirty=True, num_downloads=Greatest(F('num_downloads') - 1, 0))
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_sound_downloads=Greatest(F('num_sound_downloads') - 1, 0))


@receiver(post_save, sender=Download)
def update_num_downloads_on_insert(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        if download.sound_id:
            Sound.objects.filter(id=download.sound_id).update(
                is_index_dirty=True, num_downloads=Greatest(F('num_downloads') + 1, 0))
            accounts.models.Profile.objects.filter(user_id=download.user_id).update(
                num_sound_downloads=Greatest(F('num_sound_downloads') + 1, 0))


class PackDownload(models.Model):
    user = models.ForeignKey(User, related_name='pack_downloads', on_delete=models.CASCADE)
    pack = models.ForeignKey(Pack, related_name='downloads', on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)


class PackDownloadSound(models.Model):
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    pack_download = models.ForeignKey(PackDownload, on_delete=models.CASCADE)
    license = models.ForeignKey(License, on_delete=models.CASCADE)


@receiver(post_delete, sender=PackDownload)
def update_num_downloads_on_delete_pack(**kwargs):
    download = kwargs['instance']
    Pack.objects.filter(id=download.pack_id).update(num_downloads=Greatest(F('num_downloads') - 1, 0))
    accounts.models.Profile.objects.filter(user_id=download.user_id).update(
        num_pack_downloads=Greatest(F('num_pack_downloads') - 1, 0))


@receiver(post_save, sender=PackDownload)
def update_num_downloads_on_insert_pack(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        Pack.objects.filter(id=download.pack_id).update(num_downloads=Greatest(F('num_downloads') + 1, 0))
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_pack_downloads=Greatest(F('num_pack_downloads') + 1, 0))


class RemixGroup(models.Model):
    protovis_data = models.TextField(null=True, blank=True, default=None)
    sounds = models.ManyToManyField(Sound,
                                    symmetrical=False,
                                    related_name='remix_group',
                                    blank=True)
    group_size = models.PositiveIntegerField(null=False, default=0)


class SoundLicenseHistory(models.Model):
    """Store history of licenses related to a sound"""
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)


class SoundAnalysis(models.Model):
    """Reference to the analysis output for a given sound and extractor.
    The actual output can be either directly stored in the model (using analysis_data field),
    or can be stored in a JSON/YAML file in disk.
    """
    STATUS_CHOICES = (
            ("QU", 'Queued'),
            ("OK", 'Ok'),
            ("SK", 'Skipped'),
            ("FA", 'Failed'),
        )

    sound = models.ForeignKey(Sound, related_name='analyses', on_delete=models.CASCADE)
    last_sent_to_queue = models.DateTimeField(auto_now_add=True)
    last_analyzer_finished = models.DateTimeField(null=True)
    analyzer = models.CharField(db_index=True, max_length=255)  # Analyzer name including version
    analysis_data = JSONField(null=True)
    analysis_status = models.CharField(null=False, default="QU", db_index=True, max_length=2, choices=STATUS_CHOICES)
    num_analysis_attempts = models.IntegerField(default=0)
    analysis_time = models.FloatField(default=0)

    @property
    def analysis_filepath_base(self):
        """Returns the absolute path of the analysis files related with this SoundAnalysis object. Related files will
         include analysis output but also logs. The base filepath should be complemented with the extension, which
         could be '.json' or '.yaml' (for analysis outputs) or '.log' for log file. The related files should be in
         the ANALYSIS_PATH and under a sound ID folder structure like sounds and other sound-related files."""
        id_folder = str(old_div(self.sound_id, 1000))
        return os.path.join(settings.ANALYSIS_PATH, id_folder, f"{self.sound_id}-{self.analyzer}")

    def load_analysis_data_from_file_to_db(self):
        """This method checks the analysis output data which has been written to a file, and loads it to the
        database using the SoundAnalysis.analysis_data field. The loading of the data into DB only happens if a
        data mapping for the current analyzer has been specified in the Django settings. Note that for some analyzers
        we don't actually want the data to be loaded in the DB as it would take a lot of space."""

        def value_is_valid(value):
            # By convention in the analyzer's code, if descriptors have a value of None, these should not be loaded/indexed
            # by Freesound, therefore these should not be considered valid.
            if value is None:
                return False
            # Postgres JSON data field can not store float values of nan or inf. Ideally these values should have never
            # been outputted by the analyzers in the first place, but it can happen. We use this function here and skip
            # indexing key/value pairs where the value is not valid for Postgres JSON data fields.
            if isinstance(value, float):
                return not math.isinf(value) and not math.isnan(value)
            return True

        if self.analysis_status == "OK" and \
            'descriptors_map' in settings.ANALYZERS_CONFIGURATION.get(self.analyzer, {}):
            analysis_results = self.get_analysis_data_from_file()
            if analysis_results:
                descriptors_map = settings.ANALYZERS_CONFIGURATION[self.analyzer]['descriptors_map']
                analysis_data_for_db = {}
                for file_descriptor_key_path, db_descriptor_key, _ in descriptors_map:
                    # TODO: here we could implement support for nested keys in the analysis file, maybe by accessing
                    # TODO: nested keys with dot notation (e.g. "key1.nested_key2")
                    if file_descriptor_key_path in analysis_results:
                        value = analysis_results[file_descriptor_key_path]
                        if value_is_valid(value):
                            analysis_data_for_db[db_descriptor_key] = value
                self.analysis_data = analysis_data_for_db
            else:
                self.analysis_data = None
        self.save(update_fields=['analysis_data'])

    def get_analysis_data_from_file(self):
        """Returns the analysis data as stored in file or returns empty dict if no file exists. It tries
        extensions .json and .yaml as these are the supported formats for analysis results"""
        if os.path.exists(self.analysis_filepath_base + '.json'):
            try:
                return json.load(open(self.analysis_filepath_base + '.json'))
            except Exception:
                pass
        if os.path.exists(self.analysis_filepath_base + '.yaml'):
            try:
                return yaml.load(open(self.analysis_filepath_base + '.yaml'), Loader=yaml.cyaml.CSafeLoader)
            except Exception:
                pass
        return {}

    def get_analysis_data(self):
        """Returns the output of the analysis, either returning them from the DB or from a file in disk"""
        if self.analysis_status == "OK":
            if self.analysis_data:
                return self.analysis_data
            else:
                return self.get_analysis_data_from_file()
        return {}

    def get_analysis_logs(self):
        """Returns the logs of the analysis"""
        try:
            fid = open(self.analysis_filepath_base + '.log')
            file_contents = fid.read()
            fid.close()
            return file_contents
        except OSError:
            return 'No logs available...'

    def re_run_analysis(self, verbose=True):
        self.sound.analyze(self.analyzer, force=True, verbose=verbose)

    def __str__(self):
        return f'Analysis of sound {self.sound_id} with {self.analyzer}'

    class Meta:
        unique_together = (("sound", "analyzer")) # one sounds.SoundAnalysis object per sound<>analyzer combination

def on_delete_sound_analysis(sender, instance, **kwargs):
    # Right before deleting a SoundAnalysis object, delete also the associated log and analysis files (if any)
    for filepath in glob.glob(instance.analysis_filepath_base + '*'):
        try:
            os.remove(filepath)
        except Exception as e:
            pass

pre_delete.connect(on_delete_sound_analysis, sender=SoundAnalysis)
