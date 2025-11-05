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
import glob
import json
import logging
import math
import os
import random
import yaml
import zlib

from collections import Counter

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.postgres.expressions import ArraySubquery
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Avg, Exists, F, OuterRef, Prefetch, Sum
from django.db.models.functions import Greatest, JSONObject
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.http import urlencode
from django.utils.functional import cached_property
from django.utils.text import Truncator, slugify
from django.utils import timezone
from urllib.parse import quote

import accounts.models
from apiv2.models import ApiV2Client
from comments.models import Comment
from freesound.celery import app as celery_app
from general import tasks
from general.templatetags.absurl import url2absurl
from geotags.models import GeoTag
from ratings.models import SoundRating
from general.templatetags.util import formatnumber
from sounds.templatetags.bst_category import bst_taxonomy_category_key_to_category_names, bst_taxonomy_category_names_to_category_key
from tags.models import SoundTag, Tag
from tickets import TICKET_STATUS_CLOSED, TICKET_STATUS_NEW
from tickets.models import Ticket, TicketComment
from utils.cache import invalidate_template_cache, invalidate_user_template_caches
from utils.locations import locations_decorator
from utils.mail import send_mail_template
from utils.search import get_search_engine, SearchEngineException
from utils.search.search_sounds import delete_sounds_from_search_engine
from utils.similarity_utilities import delete_sound_from_gaia, get_similarity_search_target_vector
from utils.sound_upload import get_csv_lines, validate_input_csv_file, bulk_describe_from_csv

web_logger = logging.getLogger('web')
sounds_logger = logging.getLogger('sounds')


class License(models.Model):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=8, db_index=True)
    summary = models.TextField()
    short_summary = models.TextField(null=True)
    summary_for_describe_form = models.TextField(null=True)
    deed_url = models.URLField()
    legal_code_url = models.URLField()
    is_public = models.BooleanField(default=True)

    def get_short_summary(self):
        return self.short_summary if self.short_summary is not None else Truncator(self.summary)\
            .words(20, html=True, truncate='...')

    @staticmethod
    def bw_cc_icon_name_from_license_name(license_name):
        if '0' in license_name.lower():
            return 'zero'
        elif 'noncommercial' in license_name.lower():
            return 'by-nc'
        elif 'attribution' in license_name.lower():
            return 'by'
        elif 'sampling' in license_name.lower():
            return 'splus'
        return 'cc'

    @property
    def icon_name(self):
        return self.bw_cc_icon_name_from_license_name(self.name)

    @property
    def name_with_version(self):
        version_label = ''
        if '3.0' in self.deed_url:
            version_label = ' 3.0'
        elif '4.0' in self.deed_url:
            version_label = ' 4.0'
        name = self.name
        return f'{name}{version_label}'

    @property
    def abbreviated_name_with_version(self):
        version_label = ''
        if '3.0' in self.deed_url:
            version_label = ' 3.0'
        elif '4.0' in self.deed_url:
            version_label = ' 4.0'
        name = self.abbreviation.upper()
        if name != 'CC0' and 'SAMP+' not in name:
            name = 'CC ' + name
        name = name.replace('SAMP+', 'Sampling Plus 1.0')
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
    validation_output = models.JSONField(null=True)
    sounds_valid = models.PositiveIntegerField(null=False, default=0)
    description_output = models.JSONField(null=True)

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
            # continue with execution
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
        if n_lines_validated_ok == 0:
            # If no sounds were supposed to be described, set progress to 100
            progress = 100
        else:
            if self.description_output is not None:
                progress = (100.0 * (n_sounds_published +
                                     n_sounds_moderation +
                                     n_sounds_failed_processing +
                                     n_sounds_error +
                                     n_sounds_unknown)
                            ) / (n_sounds_described_ok +
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
            date_threshold = timezone.now()

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
                    moderation_state = 'OK' and
                    is_explicit is false and
                    greatest(created, moderation_date) > %s
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
        qs = self.bulk_query_id(sound_ids, include_audio_descriptors=True)
        comments_subquery = Comment.objects.filter(sound=OuterRef("id")).values("comment")
        is_remix_subquery = Sound.objects.filter(remixes=OuterRef("id")).values("id")
        was_remixed_subquery = Sound.objects.filter(sources=OuterRef("id")).values("id")

        qs = qs.annotate(comments_array=ArraySubquery(comments_subquery),
                         is_remix=Exists(is_remix_subquery),
                         was_remixed=Exists(was_remixed_subquery))
        return qs


    def bulk_query(self, include_audio_descriptors=False):
        tags_subquery = Tag.objects.filter(soundtag__sound=OuterRef("id")).values("name")
        analysis_subquery = SoundAnalysis.objects.filter(
            sound=OuterRef("id"), analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, analysis_status="OK"
        )
        search_engine_similarity_subquery = SoundAnalysis.objects.filter(
            sound=OuterRef("id"), analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER, analysis_status="OK"
        )

        qs = self.select_related(
            'user', 'user__profile', 'license', 'ticket', 'pack', 'geotag'
            ).annotate(
                username=F("user__username"),
                pack_name=F("pack__name"),
                remixgroup_id=F("remix_group__id"),
                tag_array=ArraySubquery(tags_subquery),
                analysis_state_essentia_exists=Exists(analysis_subquery),
                search_engine_similarity_state=Exists(search_engine_similarity_subquery)
            )

        if include_audio_descriptors:
            # By default include all consolidated audio descriptors, but if include_audio_descriptors is a list, then only include those specified
            if isinstance(include_audio_descriptors, list):
                descriptor_names = include_audio_descriptors
            else:
                descriptor_names = [descriptor['name'] for descriptor in settings.CONSOLIDATED_AUDIO_DESCRIPTORS]

            json_object_args = {descriptor_name: f'analysis_data__' + descriptor_name for descriptor_name in descriptor_names} 
            consolidated_audio_descriptors_subquery = SoundAnalysis.objects.filter(
                sound=OuterRef("id"), analyzer="consolidated", analysis_status="OK"
            ).values(data=JSONObject(**json_object_args))
            qs = qs.annotate(consolidated_audio_descriptors=ArraySubquery(consolidated_audio_descriptors_subquery))

        return qs

    def bulk_sounds_for_user(self, user_id, limit=None, include_audio_descriptors=False):
        qs = self.bulk_query(include_audio_descriptors=include_audio_descriptors)
        qs = qs.filter(
            moderation_state="OK",
            processing_state="OK",
            user_id=user_id
        ).order_by('-created')

        if limit:
            qs = qs[:limit]
        return qs

    def bulk_sounds_for_pack(self, pack_id, limit=None, include_audio_descriptors=False):
        qs = self.bulk_query(include_audio_descriptors=include_audio_descriptors)
        qs = qs.filter(
            moderation_state="OK",
            processing_state="OK",
            pack_id=pack_id
        ).order_by('-created')

        if limit:
            qs = qs[:limit]
        return qs

    def bulk_query_id(self, sound_ids, limit=None, include_audio_descriptors=False):
        if not isinstance(sound_ids, list):
            sound_ids = [sound_ids]
        qs = self.bulk_query(include_audio_descriptors=include_audio_descriptors)
        qs = qs.filter(
            id__in=sound_ids
        ).order_by('-created')

        if limit:
            qs = qs[:limit]
        return qs

    def bulk_query_id_public(self, sound_ids, limit=None, include_audio_descriptors=False):
        qs = self.bulk_query_id(sound_ids, limit=limit, include_audio_descriptors=include_audio_descriptors)
        qs = qs.filter(
            moderation_state="OK",
            processing_state="OK",
        )
        return qs

    def dict_ids(self, sound_ids, include_audio_descriptors=False):
        return {sound_obj.id: sound_obj for sound_obj in self.bulk_query_id(sound_ids, include_audio_descriptors=include_audio_descriptors)}

    def ordered_ids(self, sound_ids, include_audio_descriptors=False):
        sounds = self.dict_ids(sound_ids, include_audio_descriptors=include_audio_descriptors)
        return [sounds[sound_id] for sound_id in sound_ids if sound_id in sounds]


class PublicSoundManager(models.Manager):
    """ a class which only returns public sounds """
    def get_queryset(self):
        return super().get_queryset().filter(moderation_state="OK", processing_state="OK")


class Sound(models.Model):
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

    # user defined fields
    description = models.TextField()
    date_recorded = models.DateField(null=True, blank=True, default=None)

    # Broad Sound Taxonomy (BST) category
    bst_category = models.CharField(max_length=8, null=True, blank=True, default=None, choices=settings.BST_SUBCATEGORY_CHOICES)

    # The history of licenses for a sound is stored on SoundLicenseHistory 'license' references the last one
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None, on_delete=models.SET_NULL, related_name='sounds')
    tags = models.ManyToManyField(Tag, through=SoundTag)

    # fields for specifying if the sound was uploaded via API or via bulk upload process (or none)
    uploaded_with_apiv2_client = models.ForeignKey(
        ApiV2Client, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    uploaded_with_bulk_upload_progress = models.ForeignKey(
        BulkUploadProgress, null=True, blank=True, default=None, on_delete=models.SET_NULL)

    # file properties
    type = models.CharField(db_index=True, max_length=4, choices=settings.SOUND_TYPE_CHOICES)
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
        if self.id:
            return self.friendly_filename()
        else:
            return f"Unsaved sound: {self.original_filename}"

    @property
    def moderated_and_processed_ok(self):
        return self.moderation_state == "OK" and self.processing_state == "OK"

    def friendly_filename(self):
        filename_slug = slugify(os.path.splitext(self.original_filename)[0])
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.%s" % (self.id, username_slug, filename_slug, self.type)

    @locations_decorator()
    def locations(self):
        id_folder = str(self.id // 1000)
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
        # Returns the average raring, normalized from 0 to 5
        return self.avg_rating / 2

    def get_ratings_count_text(self):
        if self.num_ratings >= settings.MIN_NUMBER_RATINGS:
            return f'Overall rating ({ formatnumber(self.num_ratings) } rating{"s" if self.num_ratings != 1 else ""})'
        else:
            return 'Not enough ratings'

    def get_ratings_count_text_short(self):
        if self.num_ratings >= settings.MIN_NUMBER_RATINGS:
            return f'({ formatnumber(self.num_ratings) })'
        else:
            return ''

    def get_absolute_url(self):
        return reverse('sound', args=[self.user.username, smart_str(self.id)])

    @property
    def should_display_small_icons_in_second_line(self):
        # This is used in small sound players (grid display) to determine if the small icons for ratings,
        # license, downloads, etc.. should be shown in the same line of the title or in the next line
        # together with the username. If the sound title is short and also there are not many icons to show,
        # (e.g. sound has no downloads and no geotag), then we can display in the same line, otherwise in the
        # second line.
        icons_count = 1
        if self.pack_id:
            icons_count += 1
        if hasattr(self, 'geotag'):
            icons_count += 1
        if self.num_downloads:
            icons_count +=2  # Counts double as it takes more width
        if self.num_comments:
            icons_count +=2  # Counts double as it takes more width
        if self.num_ratings > settings.MIN_NUMBER_RATINGS:
            icons_count +=2  # Counts double as it takes more width
        title_num_chars = len(self.original_filename)
        if icons_count >= 6:
            return title_num_chars >= 15
        elif 3 <= icons_count < 6:
            return title_num_chars >= 23
        else:
            return title_num_chars >= 30

    @property
    def license_bw_icon_name(self):
        return self.license.icon_name

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

    @cached_property
    def attribution_texts(self):
        attribution_texts = {
                'plain_text': f'{self.original_filename} by {self.user.username} -- {url2absurl(reverse("short-sound-link", args=[self.id]))} -- License: {self.license.name_with_version}',
                'html': f'<a href="{url2absurl(self.get_absolute_url())}">{self.original_filename}</a> by <a href="{url2absurl(reverse("account", args=[self.user.username]))}">{self.user.username}</a> | License: <a href="{ self.license.deed_url }">{self.license.name_with_version}</a>',
                'json': json.dumps({
                    'sound_url': url2absurl(self.get_absolute_url()),
                    'sound_name': self.original_filename,
                    'author_url': url2absurl(reverse("account", args=[self.user.username])),
                    'author_name': self.user.username,
                    'license_url': self.license.deed_url,
                    'license_name': self.license.name_with_version,
                })
            }
        if not self.sources.exists():
            return attribution_texts
        else:
            sources_attribution_texts = [s.attribution_texts for s in self.sources.all()]
            attribution_texts['plain_text'] = "\n\n".join([attribution_texts['plain_text']] + [st['plain_text'] for st in sources_attribution_texts])
            attribution_texts['html'] = "<br>\n".join([attribution_texts['html']] + [st['html'] for st in sources_attribution_texts])
            attribution_texts['json'] = json.dumps([json.loads(attribution_texts['json'])] + [json.loads(st['json']) for st in sources_attribution_texts])
            return attribution_texts


    def get_sound_tags(self, limit=None):
        """
        Returns the tags assigned to the sound as a list of strings, e.g. ["tag1", "tag2", "tag3"]
        :param limit: The maximum number of tags to return
        """
        return [t.name for t in self.tags.all().order_by('name')[0:limit]]

    def get_sound_tags_string(self, limit=None):
        """
        Returns the tags assigned to the sound as a string with tags separated by spaces, e.g. "tag1 tag2 tag3"
        :param limit: The maximum number of tags to return
        """
        return " ".join(self.get_sound_tags(limit=limit))

    def set_tags(self, tags):
        """
        Updates the tags of the Sound object. To do that it first removes all SoundTag objects which relate the sound
        with tags which are not in the provided list of tags, and then adds the new tags.
        :param list tags: list of strings representing the new tags that the Sound object should be assigned
        """
        # remove tags that are not in the list
        for tagged_item in self.soundtag_set.select_related('tag').all():
            if tagged_item.tag.name not in tags:
                tagged_item.delete()

        # add tags that are not there yet
        current_tags = set([t.name for t in self.tags.all()])
        for tag in tags:
            if tag not in current_tags:
                (tag_object, created) = Tag.objects.get_or_create(name=tag)
                tagged_object = SoundTag.objects.create(user=self.user, tag=tag_object, sound=self)
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
                settings.EMAIL_SUBJECT_SOUND_ADDED_AS_REMIX, 'emails/email_remix_update.txt',
                {'source': source, 'action': 'added', 'remix': self},
                user_to=source.user, email_type_preference_check='new_remix')

        if old_sources != new_sources:
            self.invalidate_template_caches()

    # N.B. The set_xxx functions below are used in the distributed processing and other parts of the app where we only
    # want to save an individual field of the model to prevent overwriting other model fields.

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
        :param int samplerate: samplerate to store
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
            self.moderation_date = timezone.now()
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
            self.moderation_date = timezone.now()
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
            self.processing_date = timezone.now()
            if self.processing_log is None:
                self.processing_log = ''
            self.processing_log += f'----Processed sound {timezone.now()} - {self.id}\n{processing_log}'
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
            self.processing_date = timezone.now()
            if self.processing_log is None:
                self.processing_log = ''
            self.processing_log += f'----Processed sound {timezone.now()} - {self.id}\n{processing_log}'
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
                web_logger.info('WARNING changing owner of sound %i: Could not rename file %s because '
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
        self.soundtag_set.all().update(user=new_owner)

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

    def process_and_analyze(self, force=False, high_priority=False, countdown=0):
        """
        Process and analyze a sound if the sound has a processing state different than "OK" and/or and analysis state
        other than "OK". 'force' argument can be used to trigger processing and analysis regardless of the processing
        state and analysis state of the sound.
        The countdown parameter will add some delay before the task is executed (in seconds).
        NOTE: high_priority is not implemented and setting it has no effect
        """
        self.process(force=force, high_priority=high_priority, countdown=countdown)
        self.analyze(force=force, high_priority=high_priority)

    def process(self, force=False, skip_previews=False, skip_displays=False, high_priority=False, countdown=0):
        """
        Trigger processing of the sound if processing_state is not "OK" or force=True.
        'skip_previews' and 'skip_displays' arguments can be used to disable the computation of either of these steps.
        Processing code generates the file previews and display images as well as fills some audio fields
        of the Sound model. This method returns "True" if sound was sent to process, None otherwise.
        The countdown parameter will add some delay before the task is executed (in seconds).
        NOTE: high_priority is not implemented and setting it has no effect
        """
        if force or ((self.processing_state != "OK" or self.processing_ongoing_state != "FI")
                     and self.estimate_num_processing_attempts() <= 3):
            self.set_processing_ongoing_state("QU")
            tasks.process_sound.apply_async(kwargs=dict(sound_id=self.id, skip_previews=skip_previews, skip_displays=skip_displays), countdown=countdown)
            sounds_logger.info(f"Send sound with id {self.id} to queue 'process'")
            return True

    def estimate_num_processing_attempts(self):
        # Estimates how many processing attempts have been made by looking at the processing logs
        if self.processing_log is not None:
            return max(1, self.processing_log.count('----Processed sound'))
        else:
            return 0

    def analyze(self, analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, force=False, verbose=True, high_priority=False):

        if analyzer == "consolidated":
            # Special case for consolidated analysis
            return self.consolidate_analysis()

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
            sa.last_sent_to_queue = timezone.now()
            sa.save(update_fields=['num_analysis_attempts', 'analysis_status', 'last_sent_to_queue', 'analysis_time'])
            sound_path = self.locations('path')
            if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
                sound_path = self.locations("preview.LQ.mp3.path")
            celery_app.send_task(analyzer, kwargs={'sound_id': self.id, 'sound_path': sound_path,
                        'analysis_folder': self.locations('analysis.base_path'), 'metadata':json.dumps({
                            'duration': self.duration,
                            'tags': self.get_sound_tags(),
                            'geotag': [self.geotag.lat, self.geotag.lon] if hasattr(self, 'geotag') else None,
                        })}, queue=analyzer)
            if verbose:
                sounds_logger.info(f"Sending sound {self.id} to analyzer {analyzer}")
        else:
            if verbose:
                sounds_logger.info(f"Not sending sound {self.id} to analyzer {analyzer} as is already queued")
        return sa
    
    def consolidate_analysis(self):
        """
        This method post-processes the analysis results of all analyzers for this sound and consolidates them into a new
        SoundAnalysis object with analyzer name 'consolidated'. This consolidated analysis contains audio descriptors data
        from various analyzers that will be stored in the DB and also used for indexing in the search engine.
        """
        consolidated_analysis_object, _ = SoundAnalysis.objects.get_or_create(sound=self, analyzer='consolidated')
        current_consolidated_analysis_data = consolidated_analysis_object.analysis_data

        # Iterate over all descriptors defined in settings.CONSOLIDATED_AUDIO_DESCRIPTORS and obtain/process their values
        tmp_analyzers_data = {}
        consolidated_analysis_data = {}
        for descriptor in settings.CONSOLIDATED_AUDIO_DESCRIPTORS:

            condition = descriptor.get('condition', None)
            if condition is not None:
                if not condition(self):
                    # If condition is defined and not met, skip descriptor
                    continue
            
            # Load analyzer data stored in files in disk
            # Avoid reading the same file multiple times by caching data in tmp_analyzers_data
            analyzer = descriptor['analyzer']
            try:
                sa = self.analyses.get(analyzer=analyzer, analysis_status='OK')
            except SoundAnalysis.DoesNotExist:
                sa = None
            if sa is None:
                # This analyzer has not analyzed the sound successfully, skip descriptor
                continue
            if analyzer not in tmp_analyzers_data:
                analyzer_data = sa.get_analysis_data_from_file()
                tmp_analyzers_data[analyzer] = analyzer_data
            else:
                analyzer_data = tmp_analyzers_data[analyzer]
 
            name = descriptor['name']
            original_name = descriptor.get('original_name', None)
            get_func = descriptor.get('get_func', None)
            transformation = descriptor.get('transformation', None)
            
            if original_name is not None and get_func is not None:
                raise Exception(f"Descriptor {name} cannot have both original_name and get_func defined")

            if original_name is None and get_func is None:
                raise Exception(f"Descriptor {name} must have either original_name or get_func defined")
            
            value = None
            if original_name is not None:
                if original_name in analyzer_data:
                    value = analyzer_data[original_name]
                
            if get_func is not None:
                value = get_func(analyzer_data, self)
            
            if value is not None and transformation is not None:
                value = transformation(value, analyzer_data, self)

            if value is not None:
                consolidated_analysis_data[name] = value

        if current_consolidated_analysis_data != consolidated_analysis_data:
            # If consolidated analysis data has changed...
            # ...save SoundAnalysis object
            consolidated_analysis_object.analysis_data = consolidated_analysis_data
            consolidated_analysis_object.analysis_status = "OK"
            consolidated_analysis_object.last_analyzer_finished = timezone.now()
            consolidated_analysis_object.save()
            # ...and mark sound as index dirty so it eventually gets reindexed with new analysis data
            self.mark_index_dirty(commit=True)

        return consolidated_analysis_object

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

        for player_size in ['small', 'middle', 'big_no_info', 'small_no_info', 'minimal', 'moderation']:
             for is_authenticated in [True, False]:
                invalidate_template_cache("bw_display_sound", self.id, player_size, is_authenticated)

        invalidate_template_cache("bw_sound_page", self.id)
        invalidate_template_cache("bw_sound_page_sidebar", self.id)

    def get_geotag_name(self):
        if hasattr(self, 'geotag'):
            name = self.geotag.location_name
            if name:
                return name
            return f'{self.geotag.lat:.2f}, {self.geotag.lon:.3f}'
        return None

    @property
    def ready_for_similarity(self):
        # Returns True if the sound has been analyzed for similarity and should be available for similarity queries
        if settings.USE_SEARCH_ENGINE_SIMILARITY:
            if hasattr(self, 'search_engine_similarity_state'):
                # If attribute is precomputed from query (because Sound was retrieved using bulk_query), no need to perform extra queries
                return self.search_engine_similarity_state
            else:
                # Otherwise, check if there is a SoundAnalysis object for this sound with the correct analyzer and status
                return SoundAnalysis.objects.filter(sound_id=self.id, analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER, analysis_status='OK').exists()
        else:
            # If not using search engine based similarity, then use the old similarity_state DB field
            return self.similarity_state == "OK"

    def get_similarity_search_target_vector(self, analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER):
        # If the sound has been analyzed for similarity, returns the vector to be used for similarity search
        return get_similarity_search_target_vector(self.id, analyzer=analyzer)
    
    @property
    def category_names(self):
        if self.bst_category is None:
            # If the sound category has not been defind by user, return estimated precomputed category.
            try:
                for analysis in self.analyses.all():
                    if analysis.analyzer == settings.BST_ANALYZER_NAME:
                        if analysis.analysis_data is not None:
                            return [analysis.analysis_data['category'], analysis.analysis_data['subcategory']]
            except KeyError:
                pass
            return [None, None]
        return bst_taxonomy_category_key_to_category_names(self.bst_category)    
    
    @property
    def category_code(self):
        return bst_taxonomy_category_names_to_category_key(*self.category_names)

    @property
    def get_top_level_category_search_url(self):
        top_level_name, _ = self.category_names
        if top_level_name is not None:
            cat_filter = urlencode({'f': f'category:"{top_level_name}"'})
            return f'{reverse("sounds-search")}?{cat_filter}'
        else:
            return None

    @property
    def get_second_level_category_search_url(self):
        top_level_name, second_level_name = self.category_names 
        if second_level_name is not None:
            cat_filter = urlencode({'f': f'category:"{top_level_name}" subcategory:"{second_level_name}"'})
            return f'{reverse("sounds-search")}?{cat_filter}'
        else:
            return None

    class Meta:
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
            settings.EMAIL_SUBJECT_RANDOM_SOUND_OF_THE_SAY_CHOOSEN, 'emails/email_random_sound.txt',
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
    data = models.JSONField()


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
    if hasattr(instance, 'geotag'):
        geotag = list(GeoTag.objects.filter(pk=instance.geotag.pk).values())[0]
    data['geotag'] = geotag

    license = None
    if instance.license:
        license = list(License.objects.filter(pk=instance.license.pk).values())[0]
    data['license'] = license

    data['comments'] = list(instance.comments.values())
    data['tags'] = list(instance.soundtag_set.values())
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
    if hasattr(instance, 'geotag'):
        geotag['created'] = str(geotag['created'])
    ds.data = data
    ds.save()

    if hasattr(instance, 'geotag'):
        instance.geotag.delete()

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

    def bulk_query_id(self, pack_ids, sound_ids_for_pack_id=dict(), exclude_deleted=True):
        """
        Returns a list of Pack with some added data properties that are used in display_pack. In this way,
        a single call to bulk_query_id can be used to retrieve information from all needed packs at once and
        with a 5 total queries instead of several queries per pack.
        Note that this method does not return the results sorted as in pack_ids, to do that you should use
        the ordered_ids method below.
        """
        if not isinstance(pack_ids, list):
            pack_ids = [pack_ids]
        packs = Pack.objects.prefetch_related(
            Prefetch('sounds', queryset=Sound.public.select_related('license', 'geotag').order_by('-created')),
            Prefetch('sounds__tags'),
            Prefetch('sounds__license'),
        ).select_related('user', 'user__profile').filter(id__in=pack_ids)
        if exclude_deleted:
            packs = packs.exclude(is_deleted=True)
        num_sounds_selected_per_pack = 3
        for p in packs:
            licenses = []
            selected_sounds_data = []
            tags = []
            has_geotags = False
            sound_ids_pre_selected = sound_ids_for_pack_id.get(p.id, None)
            ratings = []
            for s in p.sounds.all():
                tags += [ti.name for ti in s.tags.all()]
                licenses.append((s.license.name, s.license.id))
                if s.num_ratings >= settings.MIN_NUMBER_RATINGS:
                    ratings.append(s.avg_rating)
                if not has_geotags and hasattr(s, 'geotag'):
                    has_geotags = True
                should_add_sound_to_selected_sounds = False
                if sound_ids_pre_selected is None:
                    if len(selected_sounds_data) < num_sounds_selected_per_pack:
                        should_add_sound_to_selected_sounds = True
                else:
                    if s.id in sound_ids_pre_selected:
                        should_add_sound_to_selected_sounds = True
                if should_add_sound_to_selected_sounds:
                    selected_sounds_data.append({
                            'id': s.id,
                            'username': p.user.username,  # Packs have same username as sounds inside pack
                            'ready_for_similarity': s.similarity_state == "OK" if not settings.USE_SEARCH_ENGINE_SIMILARITY else None,  # If using search engine similarity, this needs to be retrieved later (see below)
                            'duration': s.duration,
                            'preview_mp3': s.locations('preview.LQ.mp3.url'),
                            'preview_ogg': s.locations('preview.LQ.ogg.url'),
                            'wave': s.locations('display.wave_bw.L.url'),
                            'spectral': s.locations('display.spectral_bw.L.url'),
                            'num_ratings': s.num_ratings,
                            'avg_rating': s.avg_rating
                        })
            p.num_sounds_unpublished_precomputed = p.sounds.count() - p.num_sounds
            p.licenses_data_precomputed = ([lid for _, lid in licenses], [lname for lname, _ in licenses])
            p.pack_tags = [{'name': tag, 'count': count, 'browse_url': p.browse_pack_tag_url(tag)}
                for tag, count in Counter(tags).most_common(10)]  # See pack.get_pack_tags_bw
            p.selected_sounds_data = selected_sounds_data
            p.user_profile_locations = p.user.profile.locations()
            p.has_geotags_precomputed = has_geotags
            p.num_ratings_precomputed = len(ratings)
            p.avg_rating_precomputed = sum(ratings) / len(ratings) if len(ratings) else 0.0

        if settings.USE_SEARCH_ENGINE_SIMILARITY:
            # To save an individual query for each selected sound, we get the similarity state of all selected sounds per pack in one single extra query
            selected_sounds_ids = []
            for p in packs:
                selected_sounds_ids += [s['id'] for s in p.selected_sounds_data]
            sound_ids_ready_for_similarity = SoundAnalysis.objects.filter(sound_id__in=selected_sounds_ids, analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER, analysis_status="OK").values_list('sound_id', flat=True)
            for p in packs:
                for s in p.selected_sounds_data:
                    s['ready_for_similarity'] = s['id'] in sound_ids_ready_for_similarity

        return packs

    def dict_ids(self, pack_ids, exclude_deleted=True):
        return {pack_obj.id: pack_obj for pack_obj in self.bulk_query_id(pack_ids, exclude_deleted=exclude_deleted)}

    def ordered_ids(self, pack_ids, exclude_deleted=True):
        packs = self.dict_ids(pack_ids, exclude_deleted=exclude_deleted)
        return [packs[pack_id] for pack_id in pack_ids if pack_id in packs]

    '''
    def ordered_ids(self, pack_ids, exclude_deleted=True):
        """
        Returns a list of Pack objects with ID in pack_ids and in the same order. pack_ids can include ID duplicates
        and the returned list will also include duplicated Pack objects.

        Args:
            pack_ids (List[int]): list with the IDs of the packs to be included in the output

        Returns:
            List[Pack]: List of Pack objects

        """
        base_qs = Pack.objects.filter(id__in=pack_ids)
        if exclude_deleted:
            base_qs = base_qs.exclude(is_deleted=True)
        packs = {pack_obj.id: pack_obj for pack_obj in base_qs}
        return [packs[pack_id] for pack_id in pack_ids if pack_id in packs]
    '''


class Pack(models.Model):
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
        return reverse('pack', args=[self.user.username, smart_str(self.id)])

    def get_pack_sounds_in_search_url(self):
        return f'{reverse("sounds-search")}?f=pack_grouping:{ self.pack_filter_value() }&s=Date+added+(newest+first)&g=1'

    class Meta:
        unique_together = ('user', 'name', 'is_deleted')
        ordering = ("-created",)

    def friendly_filename(self):
        name_slug = slugify(self.name)
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.zip" % (self.id, username_slug, name_slug)

    def process(self):
        # Note, can't use sounds.public below because this is a "RelatedManager" object
        sounds = self.sounds.filter(processing_state="OK", moderation_state="OK").order_by("-created")
        self.num_sounds = sounds.count()
        if self.num_sounds:
            if sounds[0].created > self.last_updated:
                # Only update last_updated if the sound that changed was created after the packs last_updated time
                # Otherwise it could be that the pack was edited (e.g. the description was changed) after the last
                # sound was added and we could be setting the date of the sound here
                self.last_updated = sounds[0].created
        self.save()
        self.invalidate_template_caches()
        invalidate_user_template_caches(self.user_id)

    def get_pack_tags(self):
        try:
            pack_tags_counts = get_search_engine().get_pack_tags(self.user.username, self.name)
            tags = [tag for tag, count in pack_tags_counts]
            return {'tags': tags, 'num_tags': len(tags)}
        except SearchEngineException as e:
            return False
        except Exception as e:
            return False

    def pack_filter_value(self):
        return f"\"{self.id}_{quote(self.name)}\""

    def browse_pack_tag_url(self, tag):
        return reverse('tags', args=[tag]) + f'?pack_flt={self.pack_filter_value()}'

    def get_pack_tags_bw(self):
        try:
            if hasattr(self, 'pack_tags'):
                return self.pack_tags  # If precomputed from PackManager.bulk_query_id method
            else:
                pack_tags_counts = get_search_engine().get_pack_tags(self.user.username, self.name)
                return [{'name': tag, 'count': count, 'browse_url': self.browse_pack_tag_url(tag)}
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
            for sound in self.sounds.all():
                sound.invalidate_template_caches()
            self.sounds.update(pack=None, is_index_dirty=True)
        self.is_deleted = True
        self.save()

    def invalidate_template_caches(self):
        # NOTE: we're currently using no cache on pack_display as it does not seem to speed up responses
        # This might need further investigation
        for player_size in ['small', 'big']:
            invalidate_template_cache("bw_display_pack", self.id, player_size)
        invalidate_template_cache("bw_pack_stats", self.id)

    def get_attribution(self, sound_qs=None):
        #If no queryset of sounds is provided, take it from the pack
        if sound_qs is None:
            sound_qs = self.sounds.filter(processing_state="OK",
                moderation_state="OK").select_related('user', 'license')

        users = User.objects.filter(sounds__in=sound_qs).distinct()
        # Generate text file with license info
        licenses = License.objects.filter(sound__pack=self).distinct()
        attribution = render_to_string("sounds/multiple_sounds_attribution.txt",
            dict(type="Pack",
                users=users,
                object=self,
                licenses=licenses,
                sound_list=sound_qs))
        return attribution

    @property
    def avg_rating(self):
        """Return average rating of the average ratings of the sounds of the pack that have more than MIN_NUMBER_RATINGS"""
        if hasattr(self, 'avg_rating_precomputed'):
            return self.avg_rating_precomputed
        else:
            result = Sound.objects.filter(
                pack=self,
                num_ratings__gte=settings.MIN_NUMBER_RATINGS
            ).aggregate(avg=Avg('avg_rating'))
            return result['avg'] or 0

    @property
    def avg_rating_0_5(self):
        """Returns the average raring, normalized from 0 to 5"""
        return self.avg_rating / 2

    @property
    def num_ratings(self):
        # The number of ratings for a pack is the number of sounds that have >= 3 ratings
        if hasattr(self, 'num_ratings_precomputed'):
            # Comes from the bulk_query_id method in PackManager
            return self.num_ratings_precomputed
        else:
            return self.sounds.filter(num_ratings__gte=settings.MIN_NUMBER_RATINGS).count()

    def get_total_pack_sounds_length(self):
        result = self.sounds.aggregate(total_duration=Sum('duration'))
        return result['total_duration'] or 0

    def num_sounds_unpublished(self):
        if hasattr(self, 'num_sounds_unpublished_precomputed'):
            return self.num_sounds_unpublished_precomputed
        else:
            return self.sounds.count() - self.num_sounds

    @cached_property
    def licenses_data(self):
        if hasattr(self, 'licenses_data_precomputed'):
            return self.licenses_data_precomputed  # If precomputed from PackManager.bulk_query_id method
        else:
            licenses_data = list(self.sounds.select_related('license').values_list('license__name', 'license_id'))
            license_ids = [lid for _, lid in licenses_data]
            license_names = [lname for lname, _ in licenses_data]
            return license_ids, license_names

    @property
    def license_summary_name_and_id(self):
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
        return License.bw_cc_icon_name_from_license_name(license_summary_name)

    @property
    def license_summary_text(self):
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
        if hasattr(self, "has_geotags_precomputed"):
            return self.has_geotags_precomputed
        else:
            return self.sounds.exclude(geotag=None).exists()

    @property
    def should_display_small_icons_in_second_line(self):
        # See same method in Sound class more more information
        icons_count = 2
        if self.has_geotags:
            icons_count += 1
        if self.num_downloads:
            icons_count +=2  # Counts double as it takes more width
        if self.num_ratings:
            icons_count +=2  # Counts double as it takes more width
        title_num_chars = len(self.name)
        if icons_count >= 6:
            return title_num_chars >= 5
        elif 3 <= icons_count < 6:
            return title_num_chars >= 18
        else:
            return title_num_chars >= 25


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
        accounts.models.Profile.objects.filter(user_id=download.sound.user_id).update(
            num_user_sounds_downloads=Greatest(F('num_user_sounds_downloads') - 1, 0))


@receiver(post_save, sender=Download)
def update_num_downloads_on_insert(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        if download.sound_id:
            Sound.objects.filter(id=download.sound_id).update(
                is_index_dirty=True, num_downloads=Greatest(F('num_downloads') + 1, 0))
            accounts.models.Profile.objects.filter(user_id=download.user_id).update(
                num_sound_downloads=Greatest(F('num_sound_downloads') + 1, 0))
            accounts.models.Profile.objects.filter(user_id=download.sound.user_id).update(
                num_user_sounds_downloads=Greatest(F('num_user_sounds_downloads') + 1, 0))


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
    accounts.models.Profile.objects.filter(user_id=download.pack.user_id).update(
        num_user_packs_downloads=Greatest(F('num_user_packs_downloads') - 1, 0))


@receiver(post_save, sender=PackDownload)
def update_num_downloads_on_insert_pack(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        Pack.objects.filter(id=download.pack_id).update(num_downloads=Greatest(F('num_downloads') + 1, 0))
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_pack_downloads=Greatest(F('num_pack_downloads') + 1, 0))
        accounts.models.Profile.objects.filter(user_id=download.pack.user_id).update(
            num_user_packs_downloads=Greatest(F('num_user_packs_downloads') + 1, 0))


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
    analysis_data = models.JSONField(null=True)
    analysis_status = models.CharField(null=False, default="QU", db_index=True, max_length=2, choices=STATUS_CHOICES)
    num_analysis_attempts = models.IntegerField(default=0)
    analysis_time = models.FloatField(default=0)

    @property
    def analysis_filepath_base(self):
        """Returns the absolute path of the analysis files related with this SoundAnalysis object. Related files will
         include analysis output but also logs. The base filepath should be complemented with the extension, which
         could be '.json' or '.yaml' (for analysis outputs) or '.log' for log file. The related files should be in
         the ANALYSIS_PATH and under a sound ID folder structure like sounds and other sound-related files."""
        id_folder = str(self.sound_id // 1000)
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

        analysis_configuration = settings.ANALYZERS_CONFIGURATION.get(self.analyzer, {})
        if self.analysis_status == "OK" and 'descriptors_map' in analysis_configuration:
            analysis_results = self.get_analysis_data_from_file()
            if analysis_results:
                descriptors_map = analysis_configuration['descriptors_map']
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
        try:
            with open(self.analysis_filepath_base + '.json') as f:
                return json.load(f)
        except Exception:
            pass
        try:
            with open(self.analysis_filepath_base + '.yaml') as f:
                return yaml.load(f, Loader=yaml.cyaml.CSafeLoader)
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
