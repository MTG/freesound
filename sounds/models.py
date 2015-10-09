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
from django.db import models
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from django.db.models.signals import post_delete, post_save, pre_save
from django.db import connection, transaction
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from tags.models import TaggedItem, Tag
from utils.sql import DelayedQueryExecuter
from utils.text import slugify
from utils.locations import locations_decorator
from utils.search.search_general import delete_sound_from_solr
from utils.filesystem import delete_object_files
from search.views import get_pack_tags
from similarity.client import Similarity
from apiv2.models import ApiV2Client
from tickets.models import Ticket, Queue, TicketComment, LinkedContent
from tickets import TICKET_SOURCE_NEW_SOUND, TICKET_STATUS_NEW
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
        interval_query = ("and created > now() - interval '%s'" % period) if use_interval else ""
        query = """
                select
                    username,
                    sound_id,
                    extra
                from (
                select
                    (select username from auth_user where auth_user.id = user_id) as username,
                    max(id) as sound_id,
                    max(created) as created,
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

    def random(self):
        sound_count = self.filter(moderation_state="OK", processing_state="OK").count()
        if sound_count:
            offset = random.randint(0, sound_count - 1)
            cursor = connection.cursor()
            cursor.execute("""SELECT id
                               FROM sounds_sound
                              WHERE moderation_state='OK'
                                AND processing_state='OK'
                             OFFSET %d
                              LIMIT 1""" % offset)
            return cursor.fetchone()[0]
        else:
            return None

    def bulk_query(self, where, order_by, limit, args):
        query = """SELECT
          auth_user.username,
          sound.id,
          sound.type,
          sound.user_id,
          sound.original_filename,
          sound.avg_rating,
          sound.description,
          sound.moderation_state,
          sound.processing_state,
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
    user = models.ForeignKey(User, related_name='sounds')
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
    license = models.ForeignKey(License)
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None, on_delete=models.SET_NULL)
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
        ('flac', 'Flac')
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

    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE", _('Pending')),  # Sounds will only be in "PE" before the very first time they are processed
        ("OK", _('OK')),
        ("FA", _('Failed')),
    )
    PROCESSING_ONGOING_STATE_CHOICES = (
        ("QU", _('Queued')),
        ("PR", _('Processing')),
        ("FI", _('Finished')),
    )
    processing_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")
    processing_ongoing_state = models.CharField(db_index=True, max_length=2,
                                                choices=PROCESSING_ONGOING_STATE_CHOICES, default="QU")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)  # Set at last processing attempt
    processing_log = models.TextField(null=True, blank=True, default=None)  # Currently unused

    # state
    is_index_dirty = models.BooleanField(null=False, default=True)
    similarity_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")
    analysis_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")

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
                        # The alternative url is sent to the requesting browser if the clickthrough logger is activated
                        # After logging the clickthrough data, the reponse is redirected to a url stripped of the
                        # alt part. The redirect will be handled by nginx
                        url_alt=settings.PREVIEWS_URL.replace("previews", "previews_alt") + "%s/%d_%d-lq.mp3" %
                                                                                            (id_folder, self.id,
                                                                                             sound_user_id)
                    ),
                    ogg=dict(
                        path=os.path.join(settings.PREVIEWS_PATH, id_folder, "%d_%d-lq.ogg" % (self.id, sound_user_id)),
                        url=settings.PREVIEWS_URL + "%s/%d_%d-lq.ogg" % (id_folder, self.id, sound_user_id),
                        filename="%d_%d-lq.ogg" % (self.id, sound_user_id),
                        # Refer to comments in mp3.url_alt
                        url_alt=settings.PREVIEWS_URL.replace("previews", "previews_alt") + "%s/%d_%d-lq.ogg" %
                                                                                            (id_folder, self.id,
                                                                                             sound_user_id)
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
        return int(self.avg_rating*10)

    @models.permalink
    def get_absolute_url(self):
        return 'sound', (self.user.username, smart_unicode(self.id),)

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
        cursor = connection.cursor()
        cursor.execute(query)
        transaction.commit_unless_managed()

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
        field_values = [[field, info[field] if info[field] is not None else "null", False] for field in field_names]
        self.set_fields(field_values)

    def change_moderation_state(self, new_state, commit=True):
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
            if (current_state == 'OK' and new_state != 'OK') or (current_state != 'OK' and new_state == 'OK'):
                # Sound either passed from being approved to not being approved, or from not being approved to
                # being appoved. Update related stuff (must be done after save)
                # TODO: update authors' num_sounds (when not handled via trigger)
                if self.pack:
                    self.pack.process()
        else:
            # Only set moderation date
            self.moderation_date = datetime.datetime.now()
            if commit:
                self.save()

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
            if commit:
                # Update related stuff such as users' num_counts or reprocessing affected pack
                # We only do these updates if commit=True as otherwise the changes would have not been saved
                # in the DB and updates would have no effect.
                # TODO: update authors' num_sounds (when not handled via trigger)
                if self.pack:
                    self.pack.process()
        else:
            if use_set_instead_of_save:
                self.set_processing_date(datetime.datetime.now())
            else:
                self.processing_date = datetime.datetime.now()
                if commit:
                    self.save()

    def mark_index_dirty(self, commit=True):
        self.is_index_dirty = True
        if commit:
            self.save()

    def add_comment(self, comment, commit=True):
        self.comments.add(comment)
        self.num_comments += 1
        self.mark_index_dirty(commit=False)
        if commit:
            self.save()

    def post_delete_comment(self, commit=True):
        self.num_comments -= 1
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
            source=TICKET_SOURCE_NEW_SOUND,
            status=TICKET_STATUS_NEW,
            queue=Queue.objects.get(name='sound moderation'),
            sender=self.user,
            content=LinkedContent.objects.create(content_object=self),
        )
        TicketComment.objects.create(
            sender=self.user,
            text="I've uploaded %s. Please moderate!" % self.original_filename,
            ticket=ticket,
        )

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

    class Meta(SocialModel.Meta):
        ordering = ("-created", )


class DeletedSound(models.Model):
    user = models.ForeignKey(User)
    sound_id = models.IntegerField(default=0, db_index=True)


def on_delete_sound(sender, instance, **kwargs):
    if instance.moderation_state == "OK" and instance.processing_state == "OK":
        try:
            DeletedSound.objects.get_or_create(sound_id=instance.id, user=instance.user)
        except User.DoesNotExist:
            deleted_user = User.objects.get(id=settings.DELETED_USER_ID)
            DeletedSound.objects.get_or_create(sound_id=instance.id, user=deleted_user)

    try:
        if instance.geotag:
            instance.geotag.delete()
    except:
        pass

    try:
        if instance.pack:
            instance.pack.process()
    except Pack.DoesNotExist:
        '''
        It might happen when we do user.delete() to a user that has several sounds in packs that when post_delete
        signals for sounds are called, the packs have already been deleted. This is because the way in which django
        deletes all the related objects with foreign keys. When a user is deleted, its packs and sounds must be deleted
        too. Django first runs pre_delete on all objects to be deleted, then delete and then post_delete. Therefore
        it can happen that when the post_delete signal for a sound is called, the pack has already been deleted but the
        instance passed to the post_delete function still points to that pack. We can therefore safely use try/except
        here and we'll still be doing the job correctly.
        '''
        pass

    delete_sound_from_solr(instance)
    delete_object_files(instance, web_logger)

    if instance.similarity_state == 'OK':
        try:
            if Similarity.contains(instance.id):
                Similarity.delete(instance.id)
        except:
            web_logger.warn("ommitting similarity deletion for deleted sound %d" % instance.id)

    web_logger.debug("Deleted sound with id %i" % instance.id)
post_delete.connect(on_delete_sound, sender=Sound)


def recreate_pack(sender, instance, **kwargs):
    if instance.moderation_state == "OK" and instance.pack:
        instance.pack.process()
post_save.connect(recreate_pack, sender=Sound)


def set_dirty(sender, instance, **kwargs):
    instance.is_index_dirty=True
pre_save.connect(set_dirty, sender=Sound)


class PackManager(models.Manager):

    def ordered_ids(self, pack_ids, select_related=''):
        # Simplified version of ordered_ids in SoundManager (no need for custom SQL here)
        packs = {pack_obj.id: pack_obj for pack_obj in Pack.objects.select_related(select_related).filter(id__in=pack_ids)}
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

    objects = PackManager()

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return 'pack', (self.user.username, smart_unicode(self.id),)

    class Meta(SocialModel.Meta):
        unique_together = ('user', 'name')
        ordering = ("-created",)

    def friendly_filename(self):
        name_slug = slugify(self.name)
        username_slug =  slugify(self.user.username)
        return "%d__%s__%s.zip" % (self.id, username_slug, name_slug)

    @locations_decorator()
    def locations(self):
        return dict(sendfile_url=settings.PACKS_SENDFILE_URL + "%d.zip" % self.id,
                    license_url=settings.PACKS_SENDFILE_URL + "%d_license.txt" % self.id,
                    license_path=os.path.join(settings.PACKS_PATH, "%d_license.txt" % self.id),
                    path=os.path.join(settings.PACKS_PATH, "%d.txt" % self.id))

    def process(self):
        sounds = self.sound_set.filter(processing_state="OK", moderation_state="OK").order_by("-created")
        self.num_sounds = sounds.count()
        if self.num_sounds:
            self.last_updated = sounds[0].created
        self.create_license_file(pack_sounds=sounds)
        self.save()

    def create_license_file(self, pack_sounds):
        """ Create a license file containing the licenses of all sounds in the
            pack, and update the pack license_crc field, but DO NOT save the pack
        """
        from django.template.loader import render_to_string
        if len(pack_sounds)>0:
            licenses = License.objects.all()
            license_path = self.locations("license_path")
            attribution = render_to_string("sounds/pack_attribution.txt", dict(pack=self, licenses=licenses,
                                                                               sound_list=pack_sounds))
            f = open(license_path, 'w')
            f.write(attribution.encode("UTF-8"))
            f.close()
            p = subprocess.Popen(["crc32", license_path], stdout=subprocess.PIPE)
            self.license_crc = p.communicate()[0].split(" ")[0][:-1]

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

    def delete(self, using=None):
        """ This deletes all sounds in the pack as well. """
        # TODO: remove from solr?
        # delete files
        delete_object_files(self, web_logger)
        super(SocialModel, self).delete(using=using)  # super class delete


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
    user = models.ForeignKey(User)
    sound = models.ForeignKey(Sound, null=True, blank=True, default=None)
    pack = models.ForeignKey(Pack, null=True, blank=True, default=None)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)


class RemixGroup(models.Model):
    protovis_data = models.TextField(null=True, blank=True, default=None)
    sounds = models.ManyToManyField(Sound,
                                    symmetrical=False,
                                    related_name='remix_group',
                                    blank=True)
    group_size = models.PositiveIntegerField(null=False, default=0)
