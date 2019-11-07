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
import os
import random

from django.conf import settings
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django.utils.encoding import smart_unicode
from django.utils.timezone import now

import tickets.models
from apiv2.models import ApiV2Client
from bookmarks.models import Bookmark
from comments.models import Comment
from donations.models import Donation
from forum.models import Post, Thread
from general.models import SocialModel
from geotags.models import GeoTag
from messages.models import Message
from ratings.models import SoundRating
from sounds.models import DeletedSound, Sound, Pack, Download, PackDownload, BulkUploadProgress
from utils.locations import locations_decorator
from utils.mail import transform_unique_email
from utils.search.solr import SolrQuery, Solr, SolrResponseInterpreter, SolrException


class ResetEmailRequest(models.Model):
    email = models.EmailField()
    user = models.OneToOneField(User, db_index=True)


class DeletedUser(models.Model):
    """
    This model is used to store basic information about users that have been deleted or anonymized.
    """
    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150)
    email = models.CharField(max_length=200)
    date_joined = models.DateTimeField()
    last_login = models.DateTimeField(null=True)
    deletion_date = models.DateTimeField(auto_now_add=True)

    DELETION_REASON_SPAMMER = 'sp'
    DELETION_REASON_DELETED_BY_ADMIN = 'ad'
    DELETION_REASON_SELF_DELETED = 'sd'
    DELETION_REASON_CHOICES = (
        (DELETION_REASON_SPAMMER, 'Spammer'),
        (DELETION_REASON_DELETED_BY_ADMIN, 'Deleted by an admin'),
        (DELETION_REASON_SELF_DELETED, 'Self deleted')
    )
    reason = models.CharField(max_length=2, choices=DELETION_REASON_CHOICES)  # TODO: should we add db_index=True?


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
    sound_signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    has_avatar = models.BooleanField(default=False)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    has_old_license = models.BooleanField(null=False, default=False)
    not_shown_in_online_users_list = models.BooleanField(null=False, default=False)
    accepted_tos = models.BooleanField(default=False)
    last_stream_email_sent = models.DateTimeField(db_index=True, null=True, default=None, blank=True)
    last_attempt_of_sending_stream_email = models.DateTimeField(db_index=True, null=True, default=None, blank=True)

    # Fields to keep track of donation emails
    # donations_reminder_email_sent should be set to True when an email has been sent, and reset to False when user
    # makes a donation (and therefore we'll check if a new email should be sent comparing with last_donation_email_sent)
    donations_reminder_email_sent = models.BooleanField(default=False)
    last_donation_email_sent = models.DateTimeField(db_index=True, null=True, default=None, blank=True)

    # The following 4 fields are updated using django signals (methods 'update_num_downloads*')
    num_sounds = models.PositiveIntegerField(editable=False, default=0)
    num_posts = models.PositiveIntegerField(editable=False, default=0)
    num_sound_downloads = models.PositiveIntegerField(editable=False, default=0)
    num_pack_downloads = models.PositiveIntegerField(editable=False, default=0)

    # "is_anonymized_user" indicates that the user account has been anonimized and no longer contains personal data
    # This is what we do when we delete a user to still preserve statistics and information and downloads
    # "is_anonymized_user" used to be called "is_deleted_user"
    is_anonymized_user = models.BooleanField(db_index=True, default=False)

    is_adult = models.BooleanField(default=False)

    objects = ProfileManager()

    def __unicode__(self):
        return self.user.username

    def get_sameuser_object(self):
        """Returns the SameUser object where the user is involved"""
        return SameUser.objects.get(Q(main_user=self.user) | Q(secondary_user=self.user))

    def get_sameuser_main_user_or_self_user(self):
        """If the user has SameUser object, it returns the main user of SameUser, otherwise returns the current user"""
        try:
            sameuser = self.get_sameuser_object()
            return sameuser.main_user
        except SameUser.DoesNotExist:
            return self.user

    def has_shared_email(self):
        """Check if the user account associated with this profile
           has other accounts with the same email address"""
        try:
            self.get_sameuser_object()
            return True
        except SameUser.DoesNotExist:
            return False

    def get_email_for_delivery(self):
        """Returns a string with the user email address taking into account SameUser objects. This is the method that
        should for delivery when sending emails.

        Check users against SameUser table (see https://github.com/MTG/freesound/pull/763). In our process of
        removing duplicated email addresses from our users table we set up a temporary table to store the original
        email addresses of users whose email was automatically changed to prevent duplicates. Here we make sure
        that emails are sent to the user with original address and not the one we edited to prevent duplicates."""
        return self.get_sameuser_main_user_or_self_user().email

    def email_is_valid(self):
        """Returns True if the email address of the user is a valid address (did not bounce in the past and the user
        is not a deleted user). Takes into account SameUser objects (see docs of self.get_user_email).
        NOTE: we don't check that user is_active because we need to send emails to inactive users (activation emails)
        """
        user = self.get_sameuser_main_user_or_self_user()
        user_has_bounces = \
            user.email_bounces.filter(type__in=(EmailBounce.PERMANENT, EmailBounce.UNDETERMINED)).count() > 0
        return not user_has_bounces and not user.profile.is_anonymized_user

    @property
    def get_total_downloads(self):
        # We consider each pack download as a single download
        return self.num_sound_downloads + self.num_pack_downloads

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

    def email_type_enabled(self, email_type):
        """
        Checkes user email settings to determine whether emails for the email_type_name should be sent.
        If the email type has send_by_default = True it menas the email should be sent if user has no assiciated
        UserEmailSetting object for this email type. If send_by_default = False, it means the email should be sent
        if the user has a UserEmailSetting for that type. This was implemented in this way to minimize the number
        of objects that need to be created in the UserEmailSetting table.

        Args:
            email_type (EmailPreferenceType|str): EmailPreferenceType object or name of the EmailPreferenceType to check

        Returns:
            bool: True if the email type is enabled

        Raises:
            EmailPreferenceTypeNotFound: if no EmailPreferenceType exists for the given name
        """
        if not isinstance(email_type, EmailPreferenceType):
            email_type = EmailPreferenceType.objects.get(name=email_type)

        email_type_in_user_email_settings = \
            UserEmailSetting.objects.filter(user=self.user, email_type=email_type).exists()

        return (email_type.send_by_default and not email_type_in_user_email_settings) or \
               (not email_type.send_by_default and email_type_in_user_email_settings)

    def get_enabled_email_types(self):
        """
        Checks which types of emails should be sent to a user according to her preferences and returns a list with all
        enabled types.

        Returns:
            List[EmailPreferenceType]: EmailPreferenceType objects corresponding to email types enabled by the user
        """
        enabled_email_types = list()
        for email_type in EmailPreferenceType.objects.all():
            if self.email_type_enabled(email_type):
                enabled_email_types.append(email_type)

        return enabled_email_types

    def set_enabled_email_types(self, email_type_ids):
        """
        Configure user email preferences so that email types corresponding to the given list of email_type_ids are set
        to enabled for that user (and those types not included in email_type_ids set to disabled). This method takes
        into account the fact that some email types should be sent by default (i.e. have send_by_default=True) and
        some not, and creates/deletes the necessary UserEmailSetting objects.

        Args:
            email_type_ids (List[int]): IDs of the EmailPreferenceType objects corresponding to the email types that
                should be enabled for the user.
        """

        # First get current value of stream_email to know if profile.last_stream_email_sent must be set to
        # now (see below)
        stream_emails_type = EmailPreferenceType.objects.get(name='stream_emails')
        had_enabled_stream_emails = self.user.email_settings.filter(email_type=stream_emails_type).exists()

        # Now check for which email types we'll need to create UserEmailSetting objects. This will be the email types
        # which either:
        # 1) have send_by_default=False and are in email_type_ids (the object indicates email should be sent)
        email_preference_types_to_add = \
            list(EmailPreferenceType.objects.filter(send_by_default=False, id__in=email_type_ids))
        # 2) have send_by_default=True and are not in email_type_ids  (the object indicates email should not be sent)
        email_preference_types_to_add += \
            list(EmailPreferenceType.objects.filter(send_by_default=True).exclude(id__in=email_type_ids))

        # Now recreate email settings objects. Delete all existing and then create those listed in
        # email_preference_types_to_add
        self.user.email_settings.all().delete()
        for email_type in email_preference_types_to_add:
            UserEmailSetting.objects.create(user=self.user, email_type=email_type)

        # If we have just enabled stream emails, we should set last_stream_email_sent to now
        enabled_stream_emails = self.email_type_enabled(stream_emails_type)
        if not had_enabled_stream_emails and enabled_stream_emails:
            self.last_stream_email_sent = datetime.datetime.now()
            self.save()

    def get_user_tags(self):
        query = SolrQuery()
        query.set_dismax_query('')
        filter_query = 'username:\"%s\"' % self.user.username
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        query.add_facet_fields("tag")
        query.set_facet_options("tag", limit=10, mincount=1)
        solr = Solr(settings.SOLR_URL)

        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
        except SolrException as e:
            return False
        except Exception as e:
            return False

        return [{'name': tag, 'count': count} for tag, count in results.facets['tag']]

    def is_trustworthy(self):
        """
        Method used to determine whether a user can be a priori considered trustworthy (e.g. not a spammer) and we
        don't need to apply certain restrictions like asking for captcha when sending private messages.
        Returns:
            bool: True if the user is trustworthy, False otherwise.
        """
        return self.num_sounds > 0 or self.num_posts > 5 or self.user.is_superuser or self.user.is_staff

    def can_post_in_forum(self):

        # A forum moderator can always post
        if self.user.has_perm('forum.can_moderate_forum'):
            return True, ""

        user_has_posts_pending_to_moderate = self.user.posts.filter(moderation_state="NM").count() > 0
        if user_has_posts_pending_to_moderate:
            return False, "We're sorry but you can't post to the forum because you have previous posts still " \
                          "pending to moderate"

        if self.num_posts >= 1 and self.num_sounds == 0:
            today = datetime.datetime.today()
            reference_date = self.user.posts.all()[0].created

            # Do not allow posts if last post is not older than 5 minutes
            seconds_per_post = settings.LAST_FORUM_POST_MINIMUM_TIME
            if (today - self.user.posts.all().reverse()[0].created).total_seconds() < seconds_per_post:
                return False, "We're sorry but you can't post to the forum because your last post was less than 5 " \
                              "minutes ago"

            # Do not allow posts if user has already posted N posts that day
            max_posts_per_day = settings.BASE_MAX_POSTS_PER_DAY + pow((today - reference_date).days, 2)
            if self.user.posts.filter(created__range=(today-datetime.timedelta(days=1), today)).count() >= \
                    max_posts_per_day:
                return False, "We're sorry but you can't post to the forum because you exceeded your maximum number " \
                              "of posts per day"

        return True, ""

    def can_do_bulk_upload(self):
        """
        Returns True if the corresponding User is allowed to use the bulk upload feature. This will happen if one of
        the following conditions is met:
        * User has uploaded at least settings.BULK_UPLOAD_MIN_SOUNDS sounds
        * User is whitelisted
        * User has been granted special permissions for bulk upload

        Returns:
            bool: True if user can do bulk upload, False otherwise.
        """

        return self.num_sounds >= settings.BULK_UPLOAD_MIN_SOUNDS or \
               self.is_whitelisted or \
               self.user.has_perm('sounds.can_describe_in_bulk')

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

    def get_info_before_delete_user(self, include_sounds=False, include_other_related_objects=False):
        """
        This method can be called before delete_user to display to the user the
        elements that will be modified
        """

        ret = {}
        if include_sounds:
            sounds = Sound.objects.filter(user=self.user)
            packs = Pack.objects.filter(user=self.user)
            collector = NestedObjects(using='default')
            collector.collect(sounds)
            ret['deleted'] = collector
            ret['logic_deleted'] = packs
        if include_other_related_objects:
            collector = NestedObjects(using='default')
            collector.collect([self.user])
            ret['deleted'] = collector
        ret['profile'] = self
        return ret

    def delete_user(self, remove_sounds=False,
                    delete_user_object_from_db=False,
                    deletion_reason=DeletedUser.DELETION_REASON_DELETED_BY_ADMIN):
        """
        Custom method for deleting a user from Freesound.

        Depending on the use case, users can be deleted completely from DB, or anonymized by removing their personal
        data but keeping related user generated content, etc. This method handles all of that and should be always
        used instead of User.delete().

        When deleting a user using Profile.delete_user(), a DeletedUser object will be always created to leave a
        trace of when was the user deleted and what was the reason. The original User object will be preserved but all
        the personal data will be anonymized, and the user will be flagged as having been deleted.

        When deleting a user, it's sounds and packs can either be deleted or preserved (see function args description
        below). Other related content (ratings, comments, posts) will be preserved (but appear under a "deleted user"
        account).

        Optionally, a user can be fully deleted from DB including all of its packs, sounds and other relaed content.
        Even in this case a DeletedUser object will be created to keep a record.

        Args:
            remove_sounds (bool): if True the sounds created by the user will be deleted as well. Otherwise the sounds
              will still be available to other users but appear under a "deleted user" account. Defaults to False.
            delete_user_object_from_db (bool): if True the user object will be completely removed from the DB together
              with all related content. Defaults to False.
            deletion_reason (str): reason for the user being deleted. Should be one of the choices defined in
              DeletedUser.DELETION_REASON_CHOICES. Defaults to DeletedUser.DELETION_REASON_DELETED_BY_ADMIN.
        """

        # Run all deletion operations in a single transaction so if there is an error we don't create duplicate
        # DeletedUser objects
        with transaction.atomic():

            # Create a DeletedUser object to store basic information for the record
            deleted_user_object = DeletedUser.objects.create(
                user=self.user,
                username=self.user.username,
                email=self.user.email,
                date_joined=self.user.date_joined,
                last_login=self.user.last_login,
                reason=deletion_reason)

            # If UserGDPRDeletionRequest object(s) exist for that user, update their status and deleted_user property
            UserGDPRDeletionRequest.objects.filter(user_id=self.user.id)\
                .update(status="de", deleted_user=deleted_user_object)

            if delete_user_object_from_db:
                # If user is to be completely deleted from the DB, use delete() method. This will remove all
                # related objects like sounds, packs, comments, etc...
                self.user.delete()

            else:
                # If user object is not to be deleted from DB we need to anonymize it and remove sounds if requested

                # Remove personal data from the user
                self.user.username = 'deleted_user_%s' % self.user.id
                self.user.email = 'deleted_user_%s@freesound.org' % self.user.id
                self.has_avatar = False
                self.is_anonymized_user = True
                self.user.set_unusable_password()

                self.about = ''
                self.home_page = ''
                self.signature = ''
                self.geotag = None

                self.save()
                self.user.save()

                # Remove existing OldUsername objects so there are no redirects to the anonymized/deleted user page
                OldUsername.objects.filter(user=self.user).delete()

                # Remove sounds and packs if requested
                if remove_sounds:
                    Sound.objects.filter(user=self.user).delete()
                    Pack.objects.filter(user=self.user).update(is_deleted=True)
                else:
                    Sound.objects.filter(user=self.user).update(is_index_dirty=True)

    def has_content(self):
        """
        Checks if the user has created any content or used Freesound in any way that leaves any significant data.
        Typically should be used to check if it is safe to hard delete the user.
        """
        return (Sound.objects.filter(user=self.user).exists() or
                Pack.objects.filter(user=self.user).exists() or
                SoundRating.objects.filter(user=self.user).exists() or
                Download.objects.filter(user=self.user).exists() or
                PackDownload.objects.filter(user=self.user).exists() or
                Bookmark.objects.filter(user=self.user).exists() or
                Post.objects.filter(author=self.user).exists() or
                Comment.objects.filter(user=self.user).exists() or
                Donation.objects.filter(user=self.user).exists() or
                Message.objects.filter(user_from=self.user).exists() or
                BulkUploadProgress.objects.filter(user=self.user).exists() or
                ApiV2Client.objects.filter(user=self.user).exists())

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


def presave_user(sender, instance, **kwargs):
    try:
        old_username = User.objects.get(pk=instance.id).username
        if old_username.lower() != instance.username.lower():
            # We use .get_or_create below to avoid having 2 OldUsername objects with the same user/username pair
            OldUsername.objects.get_or_create(user=instance, username=old_username)
    except User.DoesNotExist:
        pass


pre_save.connect(presave_user, sender=User)


class EmailPreferenceType(models.Model):
    description = models.TextField(max_length=1024, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    send_by_default = models.BooleanField(default=True,
        help_text="Indicates if the user should receive an email, if " +
        "UserEmailSetting exists for the user then the behavior is the opposite")

    def __unicode__(self):
        return self.display_name


class UserEmailSetting(models.Model):
    user = models.ForeignKey(User, related_name="email_settings")
    email_type = models.ForeignKey(EmailPreferenceType)


class OldUsername(models.Model):
    user = models.ForeignKey(User, related_name="old_usernames")
    username = models.CharField(max_length=255, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '{0} > {1}'.format(self.username, self.user.username)


class EmailBounce(models.Model):
    user = models.ForeignKey(User, related_name="email_bounces")

    # Bounce types
    UNDETERMINED = 'UD'
    PERMANENT = 'PE'
    TRANSIENT = 'TR'
    TYPE_CHOICES = (
        (UNDETERMINED, 'Undetermined'),
        (PERMANENT, 'Permanent'),
        (TRANSIENT, 'Transient')
    )
    TYPES_INVALID = [UNDETERMINED, PERMANENT]
    type = models.CharField(db_index=True, max_length=2, choices=TYPE_CHOICES, default=UNDETERMINED)
    type_map = {t[1]: t[0] for t in TYPE_CHOICES}

    timestamp = models.DateTimeField(default=now)

    class Meta:
        ordering = ("-timestamp",)
        unique_together = ('user', 'type', 'timestamp')

    @classmethod
    def type_from_string(cls, value):
        return cls.type_map.get(value, cls.UNDETERMINED)


class UserGDPRDeletionRequest(models.Model):
    """
    This model is used to store information about deletion requests received via email and to help comply with GDPR
    """
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='gdpr_deletion_requests')
    deleted_user = models.ForeignKey(DeletedUser, null=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, null=True, blank=True)
    email = models.CharField(max_length=200)
    date_request_received = models.DateTimeField(auto_now_add=True)
    GDPR_DELETION_REQUEST_STATUSES = (
        ('re', 'Received'),
        ('wa', 'Waiting for user action'),
        ('ca', 'Request cancelled'),
        ('de', 'User has been deleted')
    )
    status = models.CharField(max_length=2, choices=GDPR_DELETION_REQUEST_STATUSES, db_index=True, default='re')
