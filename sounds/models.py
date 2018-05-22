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

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.template.loader import render_to_string
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from django.db import models, connection, transaction
from django.db.models import F
from django.db.models.signals import pre_delete, post_delete, post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from tags.models import TaggedItem, Tag
from utils.sql import DelayedQueryExecuter
from utils.cache import invalidate_template_cache
from utils.text import slugify
from utils.locations import locations_decorator
from utils.search.search_general import delete_sound_from_solr
from utils.similarity_utilities import delete_sound_from_gaia
from utils.mail import send_mail_template
from search.views import get_pack_tags
from apiv2.models import ApiV2Client
from tickets.models import Ticket, Queue, TicketComment
from comments.models import Comment
from tickets import TICKET_STATUS_CLOSED, TICKET_STATUS_NEW
import accounts.models
import os
import logging
import random
import gearman
import subprocess
import datetime


search_logger = logging.getLogger('search')
web_logger = logging.getLogger('web')
audio_logger = logging.getLogger('audio')


class License(OrderedModel):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=8, db_index=True)
    summary = models.TextField()
    deed_url = models.URLField()
    legal_code_url = models.URLField()
    is_public = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class SoundManager(models.Manager):

    def latest_additions(self, num_sounds, period='2 weeks', use_interval=True):
        interval_query = ("and greatest(created, moderation_date) > now() - interval '%s'" % period) if use_interval else ""
        query = """
                select
                    username,
                    sound_id,
                    extra
                from (
                select
                    (select username from auth_user where auth_user.id = user_id) as username,
                    max(id) as sound_id,
                    greatest(max(created), max(moderation_date)) as created,
                    count(*) - 1 as extra
                from
                    sounds_sound
                where
                    processing_state = 'OK' and
                    moderation_state = 'OK'
                    %s
                group by
                    user_id
                ) as X order by created desc limit %d;""" % (interval_query, num_sounds)
        return DelayedQueryExecuter(query)

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
        """Get data to insert into solr for many sounds in a single query"""
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
          exists(select 1 from sounds_sound_sources where from_sound_id=sound.id) as is_remix,
          exists(select 1 from sounds_sound_sources where to_sound_id=sound.id) as was_remixed,
          ARRAY(
            SELECT tags_tag.name
            FROM tags_tag
            LEFT JOIN tags_taggeditem ON tags_taggeditem.object_id = sound.id
          WHERE tags_tag.id = tags_taggeditem.tag_id
           AND tags_taggeditem.content_type_id=20) AS tag_array,
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
        WHERE
          sound.id IN %s """
        return self.raw(query, [sound_ids])

    def bulk_query(self, where, order_by, limit, args):
        query = """SELECT
          auth_user.username,
          sound.id,
          sound.type,
          sound.user_id,
          sound.original_filename,
          sound.is_explicit,
          sound.avg_rating,
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
          sounds_remixgroup_sounds.id as remixgroup_id,
          ARRAY(
            SELECT tags_tag.name
            FROM tags_tag
            LEFT JOIN tags_taggeditem ON tags_taggeditem.object_id = sound.id
          WHERE tags_tag.id = tags_taggeditem.tag_id
           AND tags_taggeditem.content_type_id=20) AS tag_array
        FROM
          sounds_sound sound
          LEFT JOIN auth_user ON auth_user.id = sound.user_id
          LEFT JOIN sounds_pack ON sound.pack_id = sounds_pack.id
          LEFT JOIN sounds_license ON sound.license_id = sounds_license.id
          LEFT OUTER JOIN sounds_remixgroup_sounds
               ON sounds_remixgroup_sounds.sound_id = sound.id
        WHERE %s """ % (where, )
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
    def get_query_set(self):
        return super(PublicSoundManager, self).get_query_set().filter(moderation_state="OK", processing_state="OK")


class Sound(SocialModel):
    user = models.ForeignKey(User, related_name="sounds")
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    # filenames
    # original_filename = name of the file the user uploaded (can be renamed on file desipction)
    # original_path = name of the file on disk before processing
    # base_filename_slug = base of the filename, this will be something like: id__username__filenameslug
    original_filename = models.CharField(max_length=512)  #
    original_path = models.CharField(max_length=512, null=True, blank=True, default=None)
    base_filename_slug = models.CharField(max_length=512, null=True, blank=True, default=None)

    # user defined fields
    description = models.TextField()
    date_recorded = models.DateField(null=True, blank=True, default=None)

    # The history of licenses for a sound is stored on SoundLicenseHistory 'license' references the last one
    license = models.ForeignKey(License)
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None, on_delete=models.SET_NULL, related_name='sounds')
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None, on_delete=models.SET_NULL)

    # uploaded with apiv2 client id (None if the sound was not uploaded using the api)
    uploaded_with_apiv2_client = models.ForeignKey(ApiV2Client, null=True, blank=True, default=None,
                                                   on_delete=models.SET_NULL)

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
        ("PE", _('Pending')),
        ("OK", _('OK')),
        ("DE", _('Deferred')),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)  # Set at last moderation state change
    moderation_note = models.TextField(null=True, blank=True, default=None)
    has_bad_description = models.BooleanField(default=False)
    is_explicit = models.BooleanField(default=False)

    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE", _('Pending')),  # Sounds will only be in "PE" before the very first time they are processed
        ("OK", _('OK')),
        ("FA", _('Failed')),
    )
    PROCESSING_ONGOING_STATE_CHOICES = (
        ("NO", _('None')),
        ("QU", _('Queued')),
        ("PR", _('Processing')),
        ("FI", _('Finished')),
    )
    ANALYSIS_STATE_CHOICES = PROCESSING_STATE_CHOICES + (("SK", _('Skipped')), ("QU", _('Queued')),)
    SIMILARITY_STATE_CHOICES = PROCESSING_STATE_CHOICES

    processing_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")
    processing_ongoing_state = models.CharField(db_index=True, max_length=2,
                                                choices=PROCESSING_ONGOING_STATE_CHOICES, default="NO")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)  # Set at last processing attempt
    processing_log = models.TextField(null=True, blank=True, default=None)  # Currently unused

    # state
    is_index_dirty = models.BooleanField(null=False, default=True)
    similarity_state = models.CharField(db_index=True, max_length=2, choices=SIMILARITY_STATE_CHOICES, default="PE")
    analysis_state = models.CharField(db_index=True, max_length=2, choices=ANALYSIS_STATE_CHOICES, default="PE")

    # counts
    num_comments = models.PositiveIntegerField(default=0)  # Updated via django (sound view and delete comment view)
    num_downloads = models.PositiveIntegerField(default=0)  # Updated via database trigger
    avg_rating = models.FloatField(default=0)  # Updated via database trigger
    num_ratings = models.PositiveIntegerField(default=0)  # Updated via database trigger

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
                )
            ),
            analysis=dict(
                statistics=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d_%d_statistics.yaml" % (self.id,
                                                                                                    sound_user_id)),
                    url=settings.ANALYSIS_URL + "%s/%d_%d_statistics.yaml" % (id_folder, self.id, sound_user_id)
                ),
                frames=dict(
                    path=os.path.join(settings.ANALYSIS_PATH, id_folder, "%d_%d_frames.json" % (self.id,
                                                                                                sound_user_id)),
                    url=settings.ANALYSIS_URL + "%s/%d_%d_frames.json" % (id_folder, self.id, sound_user_id)
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
        :param new_license: License object representing the new license
        :return:
        """
        self.license = new_license
        SoundLicenseHistory.objects.create(sound=self, license=new_license)

    # N.B. These set functions are used in the distributed processing.
    # They set a single field to prevent overwriting eachother's result in
    # the database, which is what happens if you use Django's save() method.
    def set_single_field(self, field, value, include_quotes=True):
        self.set_fields([[field, value, include_quotes]])

    def set_fields(self, fields):
        query = "UPDATE sounds_sound SET "
        query += ", ".join([('%s = %s' %
                             (field[0], (field[1] if not field[2] else ("'%s'" % field[1])))) for field in fields])
        query += " WHERE id = %s" % self.id
        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(query)

    def set_processing_state(self, state):
        self.set_single_field('processing_state', state)

    def set_processing_ongoing_state(self, state):
        self.set_single_field('processing_ongoing_state', state)

    def set_processing_date(self, date):
        self.set_single_field('processing_date', str(date))  # Date should be datetime object

    def set_analysis_state(self, state):
        self.set_single_field('analysis_state', state)

    def set_similarity_state(self, state):
        self.set_single_field('similarity_state', state)

    def set_moderation_state(self, state):
        self.set_single_field('moderation_state', state)

    def set_moderation_date(self, date):
        self.set_single_field('moderation_date', str(date))  # Date should be datetime object

    def set_original_path(self, path):
        self.set_single_field('original_path', path)

    def set_audio_info_fields(self, info):
        field_names = ['samplerate', 'bitrate', 'bitdepth', 'channels', 'duration']
        field_values = [[field, info[field], False] for field in field_names]
        self.set_fields(field_values)

    def change_moderation_state(self, new_state, commit=True, do_not_update_related_stuff=False):
        """
        Change the moderation state of a sound and perform related tasks such as marking the sound as index dirty
        or sending a pack to process if required. We do not use the similar function above 'set_moderation_state'
        to maintain consistency with other set_xxx methods in Sound model (set_xxx methods only do low-level update
        of the field, with no other checks).
        """
        current_state = self.moderation_state
        if current_state != new_state:
            self.mark_index_dirty(commit=False)
            self.moderation_state = new_state
            self.moderation_date = datetime.datetime.now()
            if commit:
                self.save()
            if new_state != "OK":
                # Sound became non approved
                self.delete_from_indexes()
            if not do_not_update_related_stuff and commit:
                if (current_state == 'OK' and new_state != 'OK') or (current_state != 'OK' and new_state == 'OK'):
                    # Sound either passed from being approved to not being approved, or from not being approved to
                    # being appoved. Update related stuff (must be done after save)
                    self.user.profile.update_num_sounds()
                    if self.pack:
                        self.pack.process()
        else:
            # Only set moderation date
            self.moderation_date = datetime.datetime.now()
            if commit:
                self.save()

        self.invalidate_template_caches()

    def change_processing_state(self, new_state, commit=True, use_set_instead_of_save=False):
        """
        Change the processing state of a sound and perform related tasks such as set the sound as index dirty if
        required. The 'use_set_instead_of_save' can be used to directly set the change of state in the db as an
        update command without affecting other fields of the Sound model. This is needed when the processing tasks
        change the processing state of the sound to avoid potential collisions when saving the whole object.
        """
        current_state = self.processing_state
        if current_state != new_state:
            # Sound either went from PE to OK, from PE to FA, from OK to FA, or from FA to OK (never from OK/FA to PE)
            self.mark_index_dirty(commit=False)
            if use_set_instead_of_save and commit:
                self.set_processing_state(new_state)
                self.set_processing_date(datetime.datetime.now())
            else:
                self.processing_state = new_state
                self.processing_date = datetime.datetime.now()
                if commit:
                    self.save()
            if new_state == "FA":
                # Sound became processing failed
                self.delete_from_indexes()
            if commit:
                # Update related stuff such as users' num_counts or reprocessing affected pack
                # We only do these updates if commit=True as otherwise the changes would have not been saved
                # in the DB and updates would have no effect.
                self.user.profile.update_num_sounds()
                if self.pack:
                    self.pack.process()
        else:
            if use_set_instead_of_save:
                self.set_processing_date(datetime.datetime.now())
            else:
                self.processing_date = datetime.datetime.now()
                if commit:
                    self.save()

        self.invalidate_template_caches()

    def change_owner(self, new_owner):
        def replace_user_id_in_path(path, old_owner_id, new_owner_id):
            old_path_beginning = '%i_%i' % (self.id, old_owner_id)
            new_path_beginning = '%i_%i' % (self.id, new_owner_id)
            return path.replace(old_path_beginning, new_path_beginning)

        # Rename related files in disk
        paths_to_rename = [
            self.locations()['path'],  # original file path
            self.locations()['analysis']['frames']['path'],  # analysis frames file
            self.locations()['analysis']['statistics']['path'],  # analysis statistics file
            self.locations()['display']['spectral']['L']['path'],  # spectrogram L
            self.locations()['display']['spectral']['M']['path'],  # spectrogram M
            self.locations()['display']['wave']['L']['path'],  # waveform L
            self.locations()['display']['wave']['M']['path'],  # waveform M
            self.locations()['preview']['HQ']['mp3']['path'],  # preview HQ mp3
            self.locations()['preview']['HQ']['ogg']['path'],  # preview HQ ogg
            self.locations()['preview']['LQ']['mp3']['path'],  # preview LQ mp3
            self.locations()['preview']['LQ']['ogg']['path'],  # preview LQ ogg
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
        self.tags.all().update(user=new_owner)

        # Change user field
        old_owner = self.user
        self.user = new_owner

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
        p = subprocess.Popen(["crc32", self.locations('path')], stdout=subprocess.PIPE)
        self.crc = p.communicate()[0].split(" ")[0][:-1]
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

    def process(self, force=False):
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        if force or self.processing_state != "OK":
            self.set_processing_ongoing_state("QU")
            gm_client.submit_job("process_sound", str(self.id), wait_until_complete=False, background=True)
            audio_logger.info("Send sound with id %s to queue 'process'" % self.id)
        if force or self.analysis_state != "OK":
            self.set_analysis_state("QU")
            gm_client.submit_job("analyze_sound", str(self.id), wait_until_complete=False, background=True)
            audio_logger.info("Send sound with id %s to queue 'analyze'" % self.id)

    def delete_from_indexes(self):
        delete_sound_from_solr(self.id)
        delete_sound_from_gaia(self)

    def invalidate_template_caches(self):
        for is_explicit in [True, False]:
            invalidate_template_cache("sound_header", self.id, is_explicit)

        for display_random_link in [True, False]:
            invalidate_template_cache("sound_footer_top", self.id, display_random_link)

        invalidate_template_cache("sound_footer_bottom", self.id)

        for is_authenticated in [True, False]:
            for is_explicit in [True, False]:
                invalidate_template_cache("display_sound", self.id, is_authenticated, is_explicit)

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
        audio_logger.info("Notifying user of random sound of the day")
        if self.email_sent:
            audio_logger.info("Email was already sent")
            return False

        if self.sound.user.profile.email_not_disabled("random_sound"):
            send_mail_template(
                u'One of your sounds has been chosen as random sound of the day!',
                'sounds/email_random_sound.txt',
                {'sound': self.sound, 'user': self.sound.user},
                None, self.sound.user.email)
            self.email_sent = True
            self.save()

        audio_logger.info("Finished sending mail to user %s of random sound of the day %s" %
                          (self.sound.user, self.sound))

        return True


class DeletedSound(models.Model):
    user = models.ForeignKey(User)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    sound_id = models.IntegerField(default=0, db_index=True)
    data = JSONField()


def on_delete_sound(sender, instance, **kwargs):
    if instance.moderation_state == "OK" and instance.processing_state == "OK":
        ds, create = DeletedSound.objects.get_or_create(
            sound_id=instance.id,
            user=instance.user,
            defaults={'data': {}})

        # Copy relevant data to DeletedSound for future research
        # Note: we do not store information about individual downloads and ratings, we only
        # store count and average (for ratings). We do not store at all information about bookmarks.

        data = Sound.objects.filter(pk=instance.pk).values()[0]
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
    # after deleted sound update num_sound on profile and pack
    try:
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

    def ordered_ids(self, pack_ids, select_related=''):
        # Simplified version of ordered_ids in SoundManager (no need for custom SQL here)
        packs = {pack_obj.id: pack_obj for pack_obj in Pack.objects.select_related(select_related)
                                                           .filter(id__in=pack_ids).exclude(is_deleted=True)}
        return [packs[pack_id] for pack_id in pack_ids if pack_id in packs]


class Pack(SocialModel):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default=None)
    is_dirty = models.BooleanField(db_index=True, default=False)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    license_crc = models.CharField(max_length=8,blank=True)
    last_updated = models.DateTimeField(db_index=True, auto_now_add=True)
    num_downloads = models.PositiveIntegerField(default=0)  # Updated via db trigger
    num_sounds = models.PositiveIntegerField(default=0)  # Updated via django Pack.process() method
    is_deleted = models.BooleanField(db_index=True, default=False)

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

    def get_random_sound_from_pack(self):
        pack_sounds = Sound.objects.filter(pack=self.id, processing_state="OK", moderation_state="OK").order_by('?')[0:1]
        return pack_sounds[0]

    def get_random_sounds_from_pack(self):
        pack_sounds = Sound.objects.filter(pack=self.id, processing_state="OK", moderation_state="OK").order_by('?')[0:3]
        return pack_sounds[0:min(3,len(pack_sounds))]

    def get_pack_tags(self, max_tags=50):
        pack_tags = get_pack_tags(self)
        if pack_tags is not False:
            tags = [t[0] for t in pack_tags['tag']]
            return {'tags': tags, 'num_tags': len(tags)}
        else:
            return -1

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


class Flag(models.Model):
    sound = models.ForeignKey(Sound)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField()
    REASON_TYPE_CHOICES = (
        ("O", _('Offending sound')),
        ("I", _('Illegal sound')),
        ("T", _('Other problem')),
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
        Sound.objects.filter(id=download.sound_id).update(num_downloads=F('num_downloads') - 1)
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_sound_downloads=F('num_sound_downloads') - 1)


@receiver(post_save, sender=Download)
def update_num_downloads_on_insert(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        if download.sound_id:
            Sound.objects.filter(id=download.sound_id).update(num_downloads=F('num_downloads') + 1)
            accounts.models.Profile.objects.filter(user_id=download.user_id).update(
                num_sound_downloads=F('num_sound_downloads') + 1)


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
    Pack.objects.filter(id=download.pack_id).update(num_downloads=F('num_downloads') - 1)
    accounts.models.Profile.objects.filter(user_id=download.user_id).update(
        num_pack_downloads=F('num_pack_downloads') - 1)


@receiver(post_save, sender=PackDownload)
def update_num_downloads_on_insert_pack(**kwargs):
    download = kwargs['instance']
    if kwargs['created']:
        Pack.objects.filter(id=download.pack_id).update(num_downloads=F('num_downloads') + 1)
        accounts.models.Profile.objects.filter(user_id=download.user_id).update(
            num_pack_downloads=F('num_pack_downloads') + 1)


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
