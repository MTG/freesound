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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import fields
from django.contrib.admin.utils import NestedObjects
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.encoding import smart_unicode
from django.conf import settings
from django.urls import reverse
from general.models import SocialModel
from geotags.models import GeoTag
from utils.search.solr import SolrQuery, Solr, SolrResponseInterpreter, SolrException
from utils.sql import DelayedQueryExecuter
from utils.locations import locations_decorator
from utils.mail import transform_unique_email
from forum.models import Post, Thread
from comments.models import Comment
from sounds.models import DeletedSound, Sound, Pack
import uuid
import tickets.models
import datetime
import random
import os


class ResetEmailRequest(models.Model):
    email = models.EmailField()
    user = models.OneToOneField(User, db_index=True)


class ProfileManager(models.Manager):

    @staticmethod
    def random_uploader():
        user_count = User.objects.filter(profile__num_sounds__gte=1).count()
        if user_count:
            offset = random.randint(0, user_count - 1)
            return User.objects.filter(profile__num_sounds__gte=1)[offset:offset+1][0]
        else:
            return None


class Profile(SocialModel):
    user = models.OneToOneField(User, related_name="profile")
    about = models.TextField(null=True, blank=True, default=None)
    home_page = models.URLField(null=True, blank=True, default=None)
    signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    has_avatar = models.BooleanField(default=False)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    has_old_license = models.BooleanField(null=False, default=False)
    not_shown_in_online_users_list = models.BooleanField(null=False, default=False)
    accepted_tos = models.BooleanField(default=False)
    last_stream_email_sent = models.DateTimeField(db_index=True, null=True, default=None)
    last_attempt_of_sending_stream_email = models.DateTimeField(db_index=True, null=True, default=None)
    last_donation_email_sent = models.DateTimeField(db_index=True, null=True, default=None)
    donations_reminder_email_sent = models.BooleanField(default=False)
    num_sounds = models.PositiveIntegerField(editable=False, default=0)  # Updated via db trigger
    num_posts = models.PositiveIntegerField(editable=False, default=0)  # Updated via db trigger
    is_deleted_user = models.BooleanField(db_index=True, default=False)
    is_adult = models.BooleanField(default=False)

    objects = ProfileManager()

    def __unicode__(self):
        return self.user.username

    def get_sameuser_object(self):
        """Returns the SameUser object where the user is involved"""
        return SameUser.objects.get(Q(main_user=self.user) | Q(secondary_user=self.user))

    def has_shared_email(self):
        """Check if the user account associated with this profile
           has other accounts with the same email address"""
        try:
            self.get_sameuser_object()
            return True
        except SameUser.DoesNotExist:
            return False

    def get_absolute_url(self):
        return reverse('account', args=[smart_unicode(self.user.username)])

    @locations_decorator(cache=False)
    def locations(self):
        id_folder = str(self.user_id/1000)
        if self.has_avatar:
            s_avatar = settings.AVATARS_URL + "%s/%d_S.jpg" % (id_folder, self.user_id)
            m_avatar = settings.AVATARS_URL + "%s/%d_M.jpg" % (id_folder, self.user_id)
            l_avatar = settings.AVATARS_URL + "%s/%d_L.jpg" % (id_folder, self.user_id)
        else:
            s_avatar = settings.MEDIA_URL + "images/32x32_avatar.png"
            m_avatar = settings.MEDIA_URL + "images/40x40_avatar.png"
            l_avatar = settings.MEDIA_URL + "images/70x70_avatar.png"
        return dict(
            avatar=dict(
                S=dict(
                    path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_S.jpg" % self.user_id),
                    url=s_avatar
                ),
                M=dict(
                    path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_M.jpg" % self.user_id),
                    url=m_avatar
                ),
                L=dict(
                    path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_L.jpg" % self.user_id),
                    url=l_avatar
                )
            ),
            uploads_dir=os.path.join(settings.UPLOADS_PATH, str(self.user_id))
        )

    def email_not_disabled(self, email_type_name):
        # Raise exception if the email_type doesn't exists
        email_type = EmailPreferenceType.objects.get(name=email_type_name)

        # when send_by_default == invert_default means email is disabled
        invert_default = UserEmailSetting.objects.filter(user=self.user,
                email_type=email_type).exists()
        return email_type.send_by_default != invert_default


    def get_enabled_email_types(self):
        # Get list of all enabled email types for this user
        all_emails = EmailPreferenceType.objects
        email_preferences = self.user.email_settings.values('email_type__id')
        # if email_type not in email_preferences then default value must be True
        not_disabled = all_emails.exclude(id__in=email_preferences)\
                .filter(send_by_default=True)

        # if email_type in email_preferences then default value must be False
        enabled = all_emails.filter(id__in=email_preferences,
                send_by_default=False)

        return set(enabled) | set(not_disabled)

    def update_enabled_email_types(self, email_type_ids):
        # Update user's email_settings from the list of enabled email_types

        stream_emails = EmailPreferenceType.objects.get(name='stream_emails')
        # First get current value of stream_email to know if
        # profile.last_stream_email_sent must be initialized
        had_enabled_stream_emails = self.user.email_settings\
                .filter(email_type=stream_emails).exists()

        all_emails = EmailPreferenceType.objects

        # If an email_type is not enabled and default value is True then must
        # be on UserEmailSetting
        disabled = all_emails.filter(send_by_default=True)\
            .exclude(id__in=email_type_ids)

        # If an email_type is enabled and default value is False then must
        # be on UserEmailSetting
        enabled = all_emails.filter(send_by_default=False,
                id__in=email_type_ids)

        all_emails = list(enabled) + list(disabled)

        # Recreate email settings
        self.user.email_settings.all().delete()
        for i in all_emails:
            UserEmailSetting.objects.create(user=self.user,
                    email_type=i)

        enabled_stream_emails = enabled.filter(id=stream_emails.id).exists()
        # If is enabling stream emails, set last_stream_email_sent to now
        if not had_enabled_stream_emails and enabled_stream_emails:
            self.last_stream_email_sent = datetime.datetime.now()
            self.save()

    def get_user_tags(self, use_solr=True):
        if use_solr:
            query = SolrQuery()
            query.set_dismax_query('')
            filter_query = 'username:\"%s\"' % self.user.username
            query.set_query_options(field_list=["id"], filter_query=filter_query)
            query.add_facet_fields("tag")
            query.set_facet_options("tag", limit=10, mincount=1)
            solr = Solr(settings.SOLR_URL)

            try:
                results = SolrResponseInterpreter(solr.select(unicode(query)))
            except SolrException, e:
                return False
            except Exception, e:
                return False

            return [{'name': tag, 'count': count} for tag, count in results.facets['tag']]

        else:
            return DelayedQueryExecuter("""
                   SELECT tags_tag.name AS name, X.c AS count
                     FROM ( SELECT tag_id, count(*) as c
                              FROM tags_taggeditem
                         LEFT JOIN sounds_sound ON object_id=sounds_sound.id
                             WHERE tags_taggeditem.user_id=%d AND
                                   sounds_sound.moderation_state='OK' AND
                                   sounds_sound.processing_state='OK'
                          GROUP BY tag_id
                          ORDER BY c
                        DESC LIMIT 10) AS X
                LEFT JOIN tags_tag ON tags_tag.id=X.tag_id
                 ORDER BY tags_tag.name;""" % self.user_id)

    def can_post_in_forum(self):
        user_has_posts_pending_to_moderate = self.user.post_set.filter(moderation_state="NM").count() > 0
        if user_has_posts_pending_to_moderate:
            return False, "We're sorry but you can't post to the forum because you have previous posts still " \
                          "pending to moderate"

        if self.user.post_set.all().count() >= 1 and self.user.sounds.all().count() == 0:
            today = datetime.datetime.today()
            reference_date = self.user.post_set.all()[0].created

            # Do not allow posts if last post is not older than 5 minutes
            seconds_per_post = 60*5
            if (today - self.user.post_set.all().reverse()[0].created).seconds < seconds_per_post:
                return False, "We're sorry but you can't post to the forum because your last post was less than 5 " \
                              "minutes ago"

            # Do not allow posts if user has already posyted N posts that day
            max_posts_per_day = 5 + pow((today - reference_date).days,2)
            if self.user.post_set.filter(created__range=(today-datetime.timedelta(days=1), today)).count() > \
                    max_posts_per_day:
                return False, "We're sorry but you can't post to the forum because you exceeded your maximum number " \
                              "of posts per day"

        return True, ""

    def is_blocked_for_spam_reports(self):
        reports_count = UserFlag.objects.filter(user__username=self.user.username).values('reporting_user').distinct().count()
        if reports_count < settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING or self.user.sounds.all().count() > 0:
            return False
        else:
            return True

    def num_sounds_pending_moderation(self):
        # Get non closed tickets with related sound objects referring to sounds
        # that have not been deleted

        return len(tickets.models.Ticket.objects.filter(\
                Q(sender=self.user) &\
                Q(sound__isnull=False) &\
                Q(sound__processing_state='OK') &\
                ~Q(sound__moderation_state='OK') &\
                ~Q(status='closed')))

    def get_info_before_delete_user(self, remove_sounds=False, remove_user=False):
        """
        This method can be called before delete_user to display to the user the
        elements that will be modified
        """

        ret = {}
        if remove_sounds:
            sounds = Sound.objects.filter(user=self.user)
            packs = Pack.objects.filter(user=self.user)
            collector = NestedObjects(using='default')
            collector.collect(sounds)
            ret['deleted'] = collector
            ret['logic_deleted'] = packs
        if remove_user:
            collector = NestedObjects(using='default')
            collector.collect([self.user])
            ret['deleted'] = collector
        ret['anonymised'] = self
        return ret

    def delete_user(self, remove_sounds=False):
        """
        User.delete() should never be called as it will completely erase the object from the db.
        Instead, Profile.delete_user() should be used (or user.profile.delete_user()).

        This method anonymise the user and flags it as deleted. If
        remove_sounds is True then the Sound (and Pack) object is removed from
        the database.
        """

        self.user.username = 'deleted_user_%s' % self.user.id
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.email = 'deleted_user_%s@freesound.org' % self.user.id
        self.has_avatar = False
        self.is_deleted_user = True
        self.user.set_password(str(uuid.uuid4()))

        self.about = ''
        self.home_page = ''
        self.signature = ''
        self.geotag = None

        self.save()
        self.user.save()
        if remove_sounds:
            Sound.objects.filter(user=self.user).delete()
            Pack.objects.filter(user=self.user).update(is_deleted=True)
        else:
            Sound.objects.filter(user=self.user).update(is_index_dirty=True)

    def update_num_sounds(self, commit=True):
        """
        Updates the num_sounds property by counting the number of moderated and processed sounds
        """
        self.num_sounds = self.user.sounds.filter(processing_state="OK", moderation_state="OK").count()
        if commit:
            self.save()

    def get_last_latlong(self):
        lasts_sound_geotagged = Sound.objects.filter(user=self.user).exclude(geotag=None).order_by('-created')
        if lasts_sound_geotagged.count():
            last_sound = lasts_sound_geotagged[0]
            return last_sound.geotag.lat, last_sound.geotag.lon, last_sound.geotag.zoom
        return None

    class Meta(SocialModel.Meta):
        ordering = ('-user__date_joined', )


class UserFlag(models.Model):
    user = models.ForeignKey(User, related_name="flags")
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"Flag %s: %s" % (self.content_type, self.object_id)

    class Meta:
        ordering = ("-user__username",)


class SameUser(models.Model):
    # Used for merging more than one user account which have the same email address

    # The main user is defined as the one who has logged in most recently
    # when we performed the migration. This is an arbitrary decision
    main_user = models.ForeignKey(User, related_name="+")
    main_orig_email = models.CharField(max_length=200)
    secondary_user = models.ForeignKey(User, related_name="+")
    secondary_orig_email = models.CharField(max_length=200)

    @property
    def orig_email(self):
        assert self.main_orig_email == self.secondary_orig_email
        return self.main_orig_email

    @property
    def main_trans_email(self):
        return self.main_orig_email  # email of main user remained unchanged

    @property
    def secondary_trans_email(self):
        return transform_unique_email(self.orig_email)

    def main_user_changed_email(self):
        return self.main_user.email != self.main_trans_email

    def secondary_user_changed_email(self):
        return self.secondary_user.email != self.secondary_trans_email


def create_user_profile(sender, instance, created, **kwargs):
    try:
        instance.profile
    except Profile.DoesNotExist:
        profile = Profile(user=instance, accepted_tos=True)
        profile.save()

post_save.connect(create_user_profile, sender=User)


class EmailPreferenceType(models.Model):
    description = models.TextField(max_length=1024, null=True, blank=True)
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    send_by_default = models.BooleanField(default=True,
        help_text="Indicates if the user should receive an email, if " +
        "UserEmailSetting exists for the user then the behavior is the opposite")

    def __unicode__(self):
        return self.display_name


class UserEmailSetting(models.Model):
    user = models.ForeignKey(User, related_name="email_settings")
    email_type = models.ForeignKey(EmailPreferenceType)
