# -*- coding: utf-8 -*-

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
import os
import random
import zlib

import gearman
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
from django.utils.encoding import smart_unicode
from django.utils.functional import cached_property
from django.utils.text import Truncator

import accounts.models
from apiv2.models import ApiV2Client
from comments.models import Comment
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from ratings.models import SoundRating
from search.views import get_pack_tags
from tags.models import TaggedItem, Tag
from tickets import TICKET_STATUS_CLOSED, TICKET_STATUS_NEW
from tickets.models import Ticket, Queue, TicketComment
from utils.cache import invalidate_template_cache
from utils.locations import locations_decorator
from utils.mail import send_mail_template
from utils.search.search_general import delete_sound_from_search_engine
from utils.similarity_utilities import delete_sound_from_gaia
from utils.sound_upload import get_csv_lines, validate_input_csv_file, bulk_describe_from_csv
from utils.text import slugify

search_logger = logging.getLogger('search')
web_logger = logging.getLogger('web')
sounds_logger = logging.getLogger('sounds')
sentry_logger = logging.getLogger('sentry')


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

    def __unicode__(self):
        return self.name


class BulkUploadProgress(models.Model):
    """Store progress status for a Bulk Describe process."""

    user = models.ForeignKey(User)
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

            sentry_logger.error('Error validating data file', exc_info=True, extra=bulk_upload_basic_data)

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
        web_logger.info('Validated data file for bulk upload (%s)' % json.dumps(bulk_upload_basic_data))

    def describe_sounds(self):
        """
        Start the actual description of the sounds and add them to Freesound.
        """
        bulk_upload_basic_data = self.get_bulk_upload_basic_data_for_log()
        web_logger.info('Started creating sound objects for bulk upload (%s)' % json.dumps(bulk_upload_basic_data))
        bulk_describe_from_csv(
            self.csv_path,
            delete_already_existing=False,
            force_import=True,
            sounds_base_dir=os.path.join(settings.UPLOADS_PATH, str(self.user_id)),
            username=self.user.username,
            bulkupload_progress_id=self.id)
        web_logger.info('Finished creating sound objects for bulk upload (%s)' % json.dumps(bulk_upload_basic_data))

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
                if type(value) == int:
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
            progress = 100.0 * (n_sounds_published +
                                n_sounds_moderation +
                                n_sounds_failed_processing +
                                n_sounds_error +
                                n_sounds_unknown) / \
                       (n_sounds_described_ok +
                        n_sounds_error +
                        n_sounds_remaining_to_describe)
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
          ac_analsyis.analysis_data as ac_analysis,
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
          LEFT JOIN sounds_soundanalysis ac_analsyis ON (sound.id = ac_analsyis.sound_id 
                                                         AND ac_analsyis.extractor = %s)
        WHERE
          sound.id IN %s """
        return self.raw(query, [ContentType.objects.get_for_model(Sound).id,
                                settings.AUDIOCOMMONS_EXTRACTOR_NAME,
                                tuple(sound_ids)])

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
          sound.analysis_state,
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
          sounds_remixgroup_sounds.id as remixgroup_id,
          accounts_profile.has_avatar as user_has_avatar,
          ac_analsyis.analysis_data as ac_analysis,
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
          LEFT JOIN sounds_soundanalysis ac_analsyis ON (sound.id = ac_analsyis.sound_id 
                                                         AND ac_analsyis.extractor = %s)
          LEFT OUTER JOIN sounds_remixgroup_sounds
               ON sounds_remixgroup_sounds.sound_id = sound.id
        WHERE %s """ % (ContentType.objects.get_for_model(Sound).id,
                        "'%s'" % settings.AUDIOCOMMONS_EXTRACTOR_NAME,
                        where, )
        if order_by:
            query = "%s ORDER BY %s" % (query, order_by)
        if limit:
            query = "%s LIMIT %s" % (query, limit)
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
        return super(PublicSoundManager, self).get_queryset().filter(moderation_state="OK", processing_state="OK")


class Sound(SocialModel):
    user = models.ForeignKey(User, related_name="sounds")
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
    license = models.ForeignKey(License)
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
    analysis_state = models.CharField(db_index=True, max_length=2, choices=ANALYSIS_STATE_CHOICES, default="PE")

    # counts, updated by django signals
    num_comments = models.PositiveIntegerField(default=0)
    num_downloads = models.PositiveIntegerField(default=0, db_index=True)
    avg_rating = models.FloatField(default=0)  # Store average rating from 0 to 10
    num_ratings = models.PositiveIntegerField(default=0)

    objects = SoundManager()
    public = PublicSoundManager()

    def __unicode__(self):
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
        id_folder = str(self.id/1000)
        sound_user_id = self.user_id
        return dict(
            path=os.path.join(settings.SOUNDS_PATH, id_folder, "%d_%d.%s" % (self.id, sound_user_id, self.type)),
            sendfile_url=settings.SOUNDS_SENDFILE_URL + "%s/%d_%d.%s" % (id_folder, self.id, sound_user_id, self.type),
            preview=dict(
                HQ=dict(
                    mp3=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-hq.mp3" % (self.id, sound_user_id)),
                        url=settings.PREVIEWS_URL + "%s/%d_%d-hq.mp3" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-hq.mp3" % (self.id, sound_user_id),
                    ),
                    ogg=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-hq.ogg" % (self.id, sound_user_id)),
                        url=settings.PREVIEWS_URL + "%s/%d_%d-hq.ogg" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-hq.ogg" % (self.id, sound_user_id),
                    )
                ),
                LQ=dict(
                    mp3=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-lq.mp3" % (self.id, sound_user_id)),
                        url=settings.PREVIEWS_URL + "%s/%d_%d-lq.mp3" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-lq.mp3" % (self.id, sound_user_id),
                    ),
                    ogg=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-lq.ogg" % (self.id, sound_user_id)),
                        url=settings.PREVIEWS_URL + "%s/%d_%d-lq.ogg" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-lq.ogg" % (self.id, sound_user_id),
                    ),
                )
            ),
            display=dict(
                spectral=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_M.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_spec_M.jpg" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_L.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_spec_L.jpg" % (id_folder, self.id, sound_user_id)
                    )
                ),
                wave=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_M.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_wave_M.png" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_L.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_wave_L.png" % (id_folder, self.id, sound_user_id)
                    )
                ),
                spectral_bw=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_bw_M.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_spec_bw_M.jpg" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_spec_bw_L.jpg" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_spec_bw_L.jpg" % (id_folder, self.id, sound_user_id)
                    )
                ),
                wave_bw=dict(
                    M=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_bw_M.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_wave_bw_M.png" % (id_folder, self.id, sound_user_id)
                    ),
                    L=dict(
                        path=os.path.join(settings.DISPLAYS_PATH, id_folder, "%d_%d_wave_bw_L.png" % (self.id,
                                                                                                   sound_user_id)),
                        url=settings.DISPLAYS_URL + "%s/%d_%d_wave_bw_L.png" % (id_folder, self.id, sound_user_id)
                    )
                )
            ),
            analysis=dict(
                statistics=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d_%d_statistics.%s" % (
                        self.id, sound_user_id, settings.ESSENTIA_STATS_OUT_FORMAT)),
                    url=settings.ANALYSIS_URL + "%s/%d_%d_statistics.%s" % (
                        id_folder, self.id, sound_user_id, settings.ESSENTIA_STATS_OUT_FORMAT)
                ),
                frames=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d_%d_frames.%s" % (
                        self.id, sound_user_id, settings.ESSENTIA_FRAMES_OUT_FORMAT)),
                    url=settings.ANALYSIS_URL + "%s/%d_%d_frames.%s" % (
                        id_folder, self.id, sound_user_id, settings.ESSENTIA_FRAMES_OUT_FORMAT)
                )
            )
        )

    def get_preview_abs_url(self):
        return 'https://%s%s' % (Site.objects.get_current().domain, self.locations()['preview']['LQ']['mp3']['url'])

    def get_thumbnail_abs_url(self, size='M'):
        return 'https://%s%s' % (Site.objects.get_current().domain, self.locations()['display']['wave'][size]['url'])

    def get_large_thumbnail_abs_url(self):
        return self.get_thumbnail_abs_url(size='L')

    def get_channels_display(self):
        if self.channels == 1:
            return u"Mono"
        elif self.channels == 2:
            return u"Stereo"
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
        return self.bitrate not in [32, 64, 96, 128, 160, 192, 224, 256, 320]

    def channels_warning(self):
        return self.channels not in [1, 2]

    def duration_ms(self):
        return self.duration * 1000

    def rating_percent(self):
        if self.num_ratings <= settings.MIN_NUMBER_RATINGS:
            return 0
        return int(self.avg_rating*10)

    @property
    def avg_rating_0_5(self):
        # Returns the average raring, normalized from 0 tp 5
        return self.avg_rating / 2

    def get_absolute_url(self):
        return reverse('sound', args=[self.user.username, smart_unicode(self.id)])

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
        return [ti.tag.name for ti in self.tags.select_related("tag").all()[0:limit]]

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

    def set_analysis_state(self, state):
        """
        Updates self.analysis_state field of the Sound object and saves to DB without updating other
        fields. This function is used in cases when two instances of the same Sound object could be edited by
        two processes in parallel and we want to avoid possible field overwrites.
        :param str state: new state to which self.analysis_state should be set
        """
        self.analysis_state = state
        self.save(update_fields=['analysis_state'])

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
            self.processing_log = processing_log
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
            self.processing_log = processing_log
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

        self.crc = '{:0>8x}'.format(crc & 0xffffffff)  # right aligned with zero-padding, width of 8 chars

        if commit:
            self.save()

    def create_moderation_ticket(self):
        ticket = Ticket.objects.create(
            title='Moderate sound %s' % self.original_filename,
            status=TICKET_STATUS_NEW,
            queue=Queue.objects.get(name='sound moderation'),
            sender=self.user,
            sound=self,
        )
        TicketComment.objects.create(
            sender=self.user,
            text="I've uploaded %s. Please moderate!" % self.original_filename,
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
        state and analysis state of the sound. 'high_priority' can be set to True to send the processing and/or
        analysis jobs with high priority to the gearman job server.
        """
        self.process(force=force, high_priority=high_priority)
        self.analyze(force=force, high_priority=high_priority)

    def process(self, force=False, skip_previews=False, skip_displays=False, high_priority=False):
        """
        Trigger processing of the sound if analysis_state is not "OK" or force=True.
        'skip_previews' and 'skip_displays' arguments can be used to disable the computation of either of these steps.
        'high_priority' argument can be set to True to send the processing job with high priority to the gearman job
        server. Processing code generates the file previews and display images as well as fills some audio fields
        of the Sound model.
        """
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        if force or self.processing_state != "OK":
            self.set_processing_ongoing_state("QU")
            gm_client.submit_job("process_sound", json.dumps({
                'sound_id': self.id,
                'skip_previews': skip_previews,
                'skip_displays': skip_displays
            }), wait_until_complete=False, background=True, priority=gearman.PRIORITY_HIGH if high_priority else None)
            sounds_logger.info("Send sound with id %s to queue 'process'" % self.id)

    def analyze(self, force=False, high_priority=False):
        """
        Trigger analysis of the sound if analysis_state is not "OK" or force=True. 'high_priority' argument can be
        set to True to send the processing job with high priority to the gearman job server. Analysis code runs
        Essentia's FreesoundExtractor and stores the results of the analysis in a JSON file.
        """
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        if force or self.analysis_state != "OK":
            self.set_analysis_state("QU")
            gm_client.submit_job("analyze_sound", json.dumps({
                'sound_id': self.id
            }), wait_until_complete=False, background=True, priority=gearman.PRIORITY_HIGH if high_priority else None)
            sounds_logger.info("Send sound with id %s to queue 'analyze'" % self.id)

    def delete_from_indexes(self):
        delete_sound_from_search_engine(self.id)
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
                for bw_player_size in ['small', 'middle', 'big_no_info', 'small_no_info']:
                    for bw_request_user_is_author in [True, False]:
                        invalidate_template_cache(
                            "bw_display_sound",
                            self.id, is_authenticated, is_explicit, bw_player_size, bw_request_user_is_author)

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
    sound = models.ForeignKey(Sound)
    date_display = models.DateField(db_index=True)
    email_sent = models.BooleanField(default=False)

    objects = SoundOfTheDayManager()

    def __unicode__(self):
        return u'Random sound of the day {0}'.format(self.date_display)

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
        data = Sound.objects.filter(pk=instance.pk).values()[0]
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
        pack = Pack.objects.filter(pk=instance.pack.pk).values()[0]
    data['pack'] = pack

    geotag = None
    if instance.geotag:
        geotag = GeoTag.objects.filter(pk=instance.geotag.pk).values()[0]
    data['geotag'] = geotag

    license = None
    if instance.license:
        license = License.objects.filter(pk=instance.license.pk).values()[0]
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
    user = models.ForeignKey(User)
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

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('pack', args=[self.user.username, smart_unicode(self.id)])

    class Meta(SocialModel.Meta):
        unique_together = ('user', 'name', 'is_deleted')
        ordering = ("-created",)

    def friendly_filename(self):
        name_slug = slugify(self.name)
        username_slug =  slugify(self.user.username)
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
        pack_tags = get_pack_tags(self)
        if pack_tags is not False:
            tags = [t[0] for t in pack_tags['tag']]
            return {'tags': tags, 'num_tags': len(tags)}
        else:
            return -1

    def get_pack_tags_bw(self):
        results = get_pack_tags(self)
        if results:
            return [{'name': tag, 'count': count} for tag, count in results['tag']]
        else:
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
            return 1.0*sum(ratings)/len(ratings)
        else:
            return 0

    @property
    def avg_rating_0_5(self):
        # Returns the average raring, normalized from 0 tp 5
        return self.avg_rating/2

    @property
    def num_ratings(self):
        # TODO: store this as pack field instead of computing it live
        return SoundRating.objects.filter(sound__pack=self).count()

    def get_total_pack_sounds_length(self):
        # TODO: don't compute this realtime, store it in DB
        durations = list(Sound.objects.filter(pack=self).values_list('duration', flat=True))
        return sum(durations)

    @cached_property
    def license_summary_name(self):
        # TODO: store this in DB?
        license_names = list(Sound.objects.filter(pack=self).values_list('license__name', flat=True))
        if len(set(license_names)) == 1:
            # All sounds have same license
            license_summary = license_names[0]
        else:
            license_summary = self.VARIOUS_LICENSES_NAME
        return license_summary

    @property
    def license_summary_text(self):
        # TODO: store this in DB?
        license_summary_name = self.license_summary_name
        if license_summary_name != self.VARIOUS_LICENSES_NAME:
            return License.objects.get(name=license_summary_name).get_short_summary
        else:
            return "This pack contains sounds released under various licenses. Please check every individual sound page " \
                   "(or the <i>readme</i> file upon downloading the pack) to know under which " \
                   "license each sound is released."

    @property
    def license_summary_deed_url(self):
        license_summary_name = self.license_summary_name
        if license_summary_name != self.VARIOUS_LICENSES_NAME:
            return License.objects.get(name=license_summary_name).deed_url
        else:
            return ""


class Flag(models.Model):
    sound = models.ForeignKey(Sound)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField()
    REASON_TYPE_CHOICES = (
        ("O", 'Offending sound'),
        ("I", 'Illegal sound'),
        ("T", 'Other problem'),
    )
    reason_type = models.CharField(max_length=1, choices=REASON_TYPE_CHOICES, default="I")
    reason = models.TextField()
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s: %s" % (self.reason_type, self.reason[:100])

    class Meta:
        ordering = ("-created",)


class Download(models.Model):
    user = models.ForeignKey(User, related_name='sound_downloads')
    sound = models.ForeignKey(Sound, related_name='downloads')
    license = models.ForeignKey(License)
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
        Sound.objects.filter(id=download.sound_id).update(num_downloads=Greatest(F('num_downloads') - 1, 0))
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_sound_downloads=Greatest(F('num_sound_downloads') - 1, 0))


@receiver(post_save, sender=Download)
def update_num_downloads_on_insert(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        if download.sound_id:
            Sound.objects.filter(id=download.sound_id).update(num_downloads=Greatest(F('num_downloads') + 1, 0))
            accounts.models.Profile.objects.filter(user_id=download.user_id).update(
                num_sound_downloads=Greatest(F('num_sound_downloads') + 1, 0))


class PackDownload(models.Model):
    user = models.ForeignKey(User, related_name='pack_downloads')
    pack = models.ForeignKey(Pack, related_name='downloads')
    created = models.DateTimeField(db_index=True, auto_now_add=True)


class PackDownloadSound(models.Model):
    sound = models.ForeignKey(Sound)
    pack_download = models.ForeignKey(PackDownload)
    license = models.ForeignKey(License)


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
    license = models.ForeignKey(License)
    sound = models.ForeignKey(Sound)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)


class SoundAnalysis(models.Model):
    """Reference to the analysis output for a given sound and extractor.
    The actual output can be either directly stored in the model (using analysis_data field),
    or can be stored in a JSON file in disk (using the analysis_filename field).

    NOTE: currently we only use this model to store the output of the Audio Commons extractor (using
    analysis_data field). We chose to implement it more generically (i.e. name the model SoundAnalysis
    instead of AudioCommonsAnalysis) so that we can use it in the future for standard Essentia analysis
    or for other extractors as well, but for the current use case that wouldn't be needed.
    """
    sound = models.ForeignKey(Sound, related_name='analyses')
    created = models.DateTimeField(auto_now_add=True)
    extractor = models.CharField(db_index=True, max_length=255)
    analysis_filename = models.CharField(max_length=255, null=True)
    analysis_data = JSONField(null=True)

    @property
    def analysis_filepath(self):
        """Returns the absolute path of the analysis file, which should be placed in the ANALYSIS_PATH
        and under a sound ID folder structure like sounds and other sound-related files."""
        id_folder = str(self.id / 1000)
        return os.path.join(settings.ANALYSIS_PATH, id_folder, "%s" % self.analysis_filename)

    def get_analysis(self):
        """Returns the contents of the analysis"""
        if self.analysis_data:
            return self.analysis_data
        elif self.analysis_filename:
            try:
                return json.load(open(self.analysis_filepath))
            except IOError:
                pass
        return None

    class Meta:
        unique_together = (("sound", "extractor"),)
