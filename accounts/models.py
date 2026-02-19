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
import typing
from urllib.parse import quote

from django.conf import settings
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_str
from psycopg.errors import ForeignKeyViolation

import tickets
from apiv2.models import ApiV2Client
from bookmarks.models import Bookmark
from comments.models import Comment
from donations.models import Donation
from forum.models import Post
from geotags.models import GeoTag
from messages.models import Message
from ratings.models import SoundRating
from sounds.models import BulkUploadProgress, Download, License, Pack, PackDownload, Sound
from utils.locations import locations_decorator
from utils.mail import transform_unique_email
from utils.search import SearchEngineException, get_search_engine

if typing.TYPE_CHECKING:
    import tickets.views


class ResetEmailRequest(models.Model):
    email = models.EmailField()
    user = models.OneToOneField(User, db_index=True, on_delete=models.CASCADE)


class DeletedUser(models.Model):
    """
    This model is used to store basic information about users that have been deleted/anonymized.
    """

    user = models.OneToOneField(User, null=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150)
    email = models.CharField(max_length=200)
    date_joined = models.DateTimeField()
    last_login = models.DateTimeField(null=True)
    deletion_date = models.DateTimeField(auto_now_add=True)
    sounds_were_also_deleted = models.BooleanField(default=False)

    DELETION_REASON_SPAMMER = "sp"
    DELETION_REASON_DELETED_BY_ADMIN = "ad"
    DELETION_REASON_SELF_DELETED = "sd"
    DELETION_REASON_CHOICES = (
        (DELETION_REASON_SPAMMER, "Spammer"),
        (DELETION_REASON_DELETED_BY_ADMIN, "Deleted by an admin"),
        (DELETION_REASON_SELF_DELETED, "Self deleted"),
    )
    reason = models.CharField(max_length=2, choices=DELETION_REASON_CHOICES)

    def __str__(self):
        return f"Deleted user object for: {self.username}"


class ProfileManager(models.Manager):
    @staticmethod
    def random_uploader():
        user_count = User.objects.filter(profile__num_sounds__gte=1).count()
        if user_count:
            offset = random.randint(0, user_count - 1)  # noqa: S311
            return User.objects.filter(profile__num_sounds__gte=1)[offset : offset + 1][0]
        else:
            return None


class Profile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    user_id: int
    about = models.TextField(null=True, blank=True, default=None)
    home_page = models.URLField(null=True, blank=True, default=None)
    signature = models.TextField(max_length=256, null=True, blank=True)
    sound_signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None, on_delete=models.SET_NULL)
    has_avatar = models.BooleanField(default=False)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    has_old_license = models.BooleanField(null=False, default=False)
    not_shown_in_online_users_list = models.BooleanField(null=False, default=False)
    accepted_tos = models.BooleanField(default=False)  # This legacy field referring to old (pre-GDPR) terms of service
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
    num_sound_downloads = models.PositiveIntegerField(
        editable=False, default=0
    )  # Number of sounds the user has downloaded
    num_pack_downloads = models.PositiveIntegerField(
        editable=False, default=0
    )  # Number of packs the user has downloaded
    num_user_sounds_downloads = models.PositiveIntegerField(
        editable=False, default=0
    )  # Number of times user's sounds have been downloaded
    num_user_packs_downloads = models.PositiveIntegerField(
        editable=False, default=0
    )  # Number of times user's packs have been downloaded

    # "is_anonymized_user" indicates that the user account has been anonymized and no longer contains personal data
    # This is what we do when we delete a user to still preserve statistics and information and downloads
    # "is_anonymized_user" used to be called "is_deleted_user"
    is_anonymized_user = models.BooleanField(db_index=True, default=False)

    # The following are user preferences that relate to how interface is displayed
    is_adult = models.BooleanField(default=False)
    allow_simultaneous_playback = models.BooleanField(default=True)
    prefer_spectrograms = models.BooleanField(default=False)
    use_compact_mode = models.BooleanField(default=False)
    UI_THEME_CHOICES = (
        ("f", "Follow system default"),
        ("l", "Light"),
        ("d", "Dark"),
    )
    ui_theme_preference = models.CharField(max_length=1, choices=UI_THEME_CHOICES, default="f")

    objects = ProfileManager()

    def __str__(self):
        return self.user.username

    def agree_to_gdpr(self):
        GdprAcceptance.objects.get_or_create(user=self.user)

    def has_sounds_with_old_cc_licenses(self):
        return self.user.sounds.select_related("license").filter(license__deed_url__contains="3.0").count() > 0

    def upgrade_old_cc_licenses_to_new_cc_licenses(self):
        old_cc_by = License.objects.get(name__iexact="Attribution", deed_url__contains="3.0")
        old_cc_by_nc = License.objects.get(name__iexact="Attribution NonCommercial", deed_url__contains="3.0")
        new_cc_by = License.objects.get(name__iexact="Attribution", deed_url__contains="4.0")
        new_cc_by_nc = License.objects.get(name__iexact="Attribution NonCommercial", deed_url__contains="4.0")
        for old_license, new_license in [(old_cc_by, new_cc_by), (old_cc_by_nc, new_cc_by_nc)]:
            self.user.sounds.filter(license=old_license).update(license=new_license)

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
        user_has_bounces = (
            user.email_bounces.filter(type__in=(EmailBounce.PERMANENT, EmailBounce.UNDETERMINED)).count() > 0
        )
        return not user_has_bounces and not user.profile.is_anonymized_user

    @property
    def get_total_downloads(self):
        # We consider each pack download as a single download
        return self.num_sound_downloads + self.num_pack_downloads

    @property
    def num_downloads_on_sounds_and_packs(self):
        # Number of downloads on user's sounds and packs
        return self.num_user_sounds_downloads + self.num_user_packs_downloads

    @property
    def num_comments(self):
        return Comment.objects.filter(user=self.user).count()

    def get_absolute_url(self):
        return reverse("account", args=[smart_str(self.user.username)])

    def get_user_sounds_in_search_url(self):
        return f'{reverse("sounds-search")}?f=username:"{quote(self.user.username)}"&s=Date+added+(newest+first)&g=0'

    def get_user_packs_in_search_url(self):
        return (
            f'{reverse("sounds-search")}?f=username:"{quote(self.user.username)}"&s=Date+added+(newest+first)&g=1&dp=1'
        )

    def get_latest_packs_for_profile_page(self):
        latest_pack_ids = (
            Pack.objects.select_related()
            .filter(user=self.user, num_sounds__gt=0)
            .exclude(is_deleted=True)
            .order_by("-last_updated")
            .values_list("id", flat=True)[0:15]
        )
        return Pack.objects.ordered_ids(pack_ids=latest_pack_ids)

    @staticmethod
    def locations_static(user_id, has_avatar):
        id_folder = str(user_id // 1000)
        if has_avatar:
            s_avatar = settings.AVATARS_URL + "%s/%d_S.jpg" % (id_folder, user_id)
            m_avatar = settings.AVATARS_URL + "%s/%d_M.jpg" % (id_folder, user_id)
            l_avatar = settings.AVATARS_URL + "%s/%d_L.jpg" % (id_folder, user_id)
            xl_avatar = settings.AVATARS_URL + "%s/%d_XL.jpg" % (id_folder, user_id)
        else:
            s_avatar = None
            m_avatar = None
            l_avatar = None
            xl_avatar = None
        return dict(
            avatar=dict(
                S=dict(path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_S.jpg" % user_id), url=s_avatar),
                M=dict(path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_M.jpg" % user_id), url=m_avatar),
                L=dict(path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_L.jpg" % user_id), url=l_avatar),
                XL=dict(path=os.path.join(settings.AVATARS_PATH, id_folder, "%d_XL.jpg" % user_id), url=xl_avatar),
            ),
            uploads_dir=os.path.join(settings.UPLOADS_PATH, str(user_id)),
        )

    @locations_decorator(cache=False)
    def locations(self):
        return Profile.locations_static(self.user_id, self.has_avatar)

    def email_type_enabled(self, email_type):
        """
        Checks user email settings to determine whether emails for the email_type_name should be sent.
        If the email type has send_by_default = True it means the email should be sent if user has no associated
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

        email_type_in_user_email_settings = UserEmailSetting.objects.filter(
            user=self.user, email_type=email_type
        ).exists()

        return (email_type.send_by_default and not email_type_in_user_email_settings) or (
            not email_type.send_by_default and email_type_in_user_email_settings
        )

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
        stream_emails_type = EmailPreferenceType.objects.get(name="stream_emails")
        had_enabled_stream_emails = self.user.email_settings.filter(email_type=stream_emails_type).exists()

        # Now check for which email types we'll need to create UserEmailSetting objects. This will be the email types
        # which either:
        # 1) have send_by_default=False and are in email_type_ids (the object indicates email should be sent)
        email_preference_types_to_add = list(
            EmailPreferenceType.objects.filter(send_by_default=False, id__in=email_type_ids)
        )
        # 2) have send_by_default=True and are not in email_type_ids  (the object indicates email should not be sent)
        email_preference_types_to_add += list(
            EmailPreferenceType.objects.filter(send_by_default=True).exclude(id__in=email_type_ids)
        )

        # Now recreate email settings objects. Delete all existing and then create those listed in
        # email_preference_types_to_add
        self.user.email_settings.all().delete()
        for email_type in email_preference_types_to_add:
            UserEmailSetting.objects.create(user=self.user, email_type=email_type)

        # If we have just enabled stream emails, we should set last_stream_email_sent to now
        enabled_stream_emails = self.email_type_enabled(stream_emails_type)
        if not had_enabled_stream_emails and enabled_stream_emails:
            self.last_stream_email_sent = timezone.now()
            self.save()

    def get_user_tags(self):
        try:
            search_engine = get_search_engine()
            tags_counts = search_engine.get_user_tags(self.user.username)
            return [
                {
                    "name": tag,
                    "count": count,
                    "browse_url": reverse("tags", args=[tag]) + f"?username_flt={self.user.username}",
                }
                for tag, count in tags_counts
            ]
        except SearchEngineException:
            return False
        except Exception:
            return False

    def is_trustworthy(self):
        """
        Method used to determine whether a user can be a priori considered trustworthy (e.g. not a spammer) and we
        don't need to apply certain restrictions like asking for captcha when sending private messages.
        Returns:
            bool: True if the user is trustworthy, False otherwise.
        """
        return (
            self.num_sounds > 0
            or self.num_posts > 5
            or self.user.is_superuser
            or self.user.is_staff
            or self.is_whitelisted
        )

    def can_post_in_forum(self):
        # A forum moderator can always post
        if self.user.has_perm("forum.can_moderate_forum"):
            return True, ""

        user_has_posts_pending_to_moderate = self.user.posts.filter(moderation_state="NM").count() > 0
        if user_has_posts_pending_to_moderate:
            return (
                False,
                "We're sorry but you can't post to the forum because you have previous posts still pending to moderate",
            )

        if self.num_posts >= 1 and self.num_sounds == 0:
            now = timezone.now()
            reference_date = self.user.posts.all()[0].created

            # Do not allow posts if last post is not older than 5 minutes
            seconds_per_post = settings.LAST_FORUM_POST_MINIMUM_TIME
            if (now - self.user.posts.all().reverse()[0].created).total_seconds() < seconds_per_post:
                return (
                    False,
                    "We're sorry but you can't post to the forum because your last post was less than 5 minutes ago",
                )

            # Do not allow posts if user has already posted N posts that day
            max_posts_per_day = settings.BASE_MAX_POSTS_PER_DAY + pow((now - reference_date).days, 2)
            if (
                self.user.posts.filter(created__range=(now - datetime.timedelta(days=1), now)).count()
                >= max_posts_per_day
            ):
                return (
                    False,
                    "We're sorry but you can't post to the forum because you exceeded your maximum number "
                    "of posts per day",
                )

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

        return (
            self.num_sounds >= settings.BULK_UPLOAD_MIN_SOUNDS
            or self.is_whitelisted
            or self.user.has_perm("sounds.can_describe_in_bulk")
        )

    def is_blocked_for_spam_reports(self):
        reports_count = (
            UserFlag.objects.filter(user__username=self.user.username).values("reporting_user").distinct().count()
        )
        if reports_count < settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING or self.user.sounds.all().count() > 0:
            return False
        else:
            return True

    def num_sounds_pending_moderation(self):
        return tickets.views._get_pending_tickets_for_user_base_qs(self.user).count()

    def get_info_before_delete_user(self, include_sounds=False, include_other_related_objects=False):
        """
        This method can be called before delete_user to display to the user the
        elements that will be modified
        """
        ret = {}
        if include_sounds:
            sounds = Sound.objects.filter(user=self.user)
            packs = Pack.objects.filter(user=self.user)
            collector = NestedObjects(using="default")
            collector.collect(sounds)
            collector.collect(packs)
            ret["deleted"] = collector
        if include_other_related_objects:
            collector = NestedObjects(using="default")
            collector.collect([self.user])
            ret["deleted"] = collector
        ret["profile"] = self
        return ret

    def delete_user(
        self,
        remove_sounds=False,
        delete_user_object_from_db=False,
        deletion_reason=DeletedUser.DELETION_REASON_DELETED_BY_ADMIN,
        chunk_size=100,
    ):
        """
        Custom method for deleting a user from Freesound.

        Depending on the use case, users can be deleted completely from DB, or anonymized by removing their personal
        data but keeping related user generated content, etc. This method handles all of that and should be always
        used instead of User.delete().

        When deleting a user using Profile.delete_user(), a DeletedUser object will be always created to leave a
        trace of when was the user deleted and what was the reason. The original User object will be preserved but all
        the personal data will be anonymized, and the user will be flagged as having been deleted.

        When deleting a user, its sounds and packs can either be deleted or preserved (see function args description
        below). Other related content (ratings, comments, posts) will be preserved (but appear under a "deleted user"
        account).

        Optionally, a user can be fully deleted from DB including all of its packs, sounds and other related content.
        Even in this case a DeletedUser object will be created to keep a record.

        Args:
            remove_sounds (bool): if True the sounds created by the user will be deleted as well. Otherwise the sounds
              will still be available to other users but appear under a "deleted user" account. Defaults to False.
            delete_user_object_from_db (bool): if True the user object will be completely removed from the DB together
              with all related content. Defaults to False.
            deletion_reason (str): reason for the user being deleted. Should be one of the choices defined in
              DeletedUser.DELETION_REASON_CHOICES. Defaults to DeletedUser.DELETION_REASON_DELETED_BY_ADMIN.
            chunk_size (int): size of the chunks in which sounds will be deleted inside atomic transactions.
        """

        # If required, start by deleting all user's sounds and packs
        if remove_sounds:
            Pack.objects.filter(user=self.user).update(is_deleted=True)
            num_sounds = Sound.objects.filter(user=self.user).count()
            num_errors = 0
            max_while_loop_errors = num_sounds // chunk_size + 1
            while num_sounds > 0 and num_errors < max_while_loop_errors:
                chunk_ids = Sound.objects.filter(user=self.user).values_list("id", flat=True)[0:chunk_size]
                with transaction.atomic():
                    try:
                        Sound.objects.filter(id__in=chunk_ids).delete()
                    except (IntegrityError, ForeignKeyViolation):
                        num_errors += 1
                num_sounds = Sound.objects.filter(user=self.user).count()

            if Sound.objects.filter(user=self.user).count() > 0:
                raise Exception("Could not delete all sounds from user {0}".format(self.user.username))

        # Now run all deletion operations related to the user (except for sounds/packs).
        # Run them in a single transaction so if there is an error we don't create duplicate
        # DeletedUser objects
        with transaction.atomic():
            # Create a DeletedUser object to store basic information for the record (first check if it
            # already exists because user was deleted previously but db object preserved
            try:
                deleted_user_object = DeletedUser.objects.get(user=self.user)
            except DeletedUser.DoesNotExist:
                deleted_user_object = DeletedUser.objects.create(
                    user=self.user,
                    username=self.user.username,
                    email=self.user.email,
                    date_joined=self.user.date_joined,
                    last_login=self.user.last_login,
                    sounds_were_also_deleted=remove_sounds,
                    reason=deletion_reason,
                )

            # Before deleting the user from db or anonymizing it, get a list of all UserDeletionRequest that will need
            # to be updated once the user has been deleted (we do that because if the user gets deleted from DB, the
            # 'user_to' field in UserDeletionRequest will be set to null and the therefore query below would not get
            # all UserDeletionRequest that we want
            udr_to_update_ids = list(
                UserDeletionRequest.objects.filter(user_to_id=self.user.id).values_list("id", flat=True)
            )

            if delete_user_object_from_db:
                # If user is to be completely deleted from the DB, use delete() method. This will remove all
                # related objects like sounds, packs, comments, etc...
                # NOTE: to prevent some possible issues because of the order in which objects are deleted, we first
                # remove all the sounds of the user (and then Django removes the user object).
                Sound.objects.filter(user=self.user).delete()
                self.user.delete()

            else:
                # If user object is not to be deleted from DB we need to anonymize it and remove sounds if requested

                # Remove personal data from the user
                self.user.username = f"deleted_user_{self.user.id}"
                self.user.email = f"deleted_user_{self.user.id}@freesound.org"
                self.has_avatar = False
                self.is_anonymized_user = True
                self.user.set_unusable_password()

                self.about = ""
                self.home_page = ""
                self.signature = ""
                self.geotag = None

                self.save()
                self.user.save()

                # Remove existing OldUsername objects so there are no redirects to the anonymized/deleted user page
                OldUsername.objects.filter(user=self.user).delete()

                if not remove_sounds:
                    Sound.objects.filter(user=self.user).update(is_index_dirty=True)

            # If UserDeletionRequest object(s) exist for that user, update the status and set deleted_user property
            # NOTE: don't use QuerySet.update method because this won't trigger the pre_save/post_save signals
            for udr in UserDeletionRequest.objects.filter(id__in=udr_to_update_ids):
                udr.status = UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED
                udr.deleted_user = deleted_user_object
                udr.save()

    def has_content(self):
        """
        Checks if the user has created any content or used Freesound in any way that leaves any significant data.
        Typically should be used to check if it is safe to hard delete the user.
        """
        return (
            Sound.objects.filter(user=self.user).exists()
            or Pack.objects.filter(user=self.user).exists()
            or SoundRating.objects.filter(user=self.user).exists()
            or Download.objects.filter(user=self.user).exists()
            or PackDownload.objects.filter(user=self.user).exists()
            or Bookmark.objects.filter(user=self.user).exists()
            or Post.objects.filter(author=self.user).exists()
            or Comment.objects.filter(user=self.user).exists()
            or Donation.objects.filter(user=self.user).exists()
            or Message.objects.filter(user_from=self.user).exists()
            or BulkUploadProgress.objects.filter(user=self.user).exists()
            or ApiV2Client.objects.filter(user=self.user).exists()
        )

    def update_num_sounds(self, commit=True):
        """
        Updates the num_sounds property by counting the number of moderated and processed sounds
        """
        self.num_sounds = self.user.sounds.filter(processing_state="OK", moderation_state="OK").count()
        if commit:
            self.save()

    def get_last_latlong(self):
        last_sound = Sound.objects.filter(user=self.user).exclude(geotag=None).order_by("-created").first()
        if last_sound:
            return last_sound.geotag.lat, last_sound.geotag.lon, last_sound.geotag.zoom
        return None

    @property
    def has_geotags(self):
        # Returns whether or not the user has geotags
        # This is used in the profile page to decide whether or not to show the geotags map. Doing this generates one
        # extra DB query, but avoid doing unnecessary map loads and a request to get all geotags by a user (which would
        # return empty query set if no geotags and indeed generate more queries).
        return Sound.objects.filter(user=self.user).exclude(geotag=None).count() > 0

    @property
    def avg_rating(self):
        """Returns the average rating from 0 to 10"""
        avg = SoundRating.objects.filter(sound__user=self.user).aggregate(models.Avg("rating"))["rating__avg"]
        return avg if avg is not None else 0

    @property
    def avg_rating_0_5(self):
        """Returns the average raring, normalized from 0 to 5"""
        return self.avg_rating / 2

    def get_total_uploaded_sounds_length(self):
        # NOTE: this only includes duration of sounds that have been processed and moderated
        durations = list(Sound.public.filter(user=self.user).values_list("duration", flat=True))
        return sum(durations)

    @property
    def num_packs(self):
        # Return the number of packs for which at least one sound has been published
        return Sound.public.filter(user=self.user).exclude(pack=None).order_by("pack_id").distinct("pack").count()

    def get_stats_for_profile_page(self):
        # Return a dictionary of user statistics to show on the user profile page
        # Because some stats are expensive to compute, we cache them
        stats_from_db = {
            "num_sounds": self.num_sounds,
            "num_downloads": self.num_downloads_on_sounds_and_packs,
            "num_posts": self.num_posts,
        }
        stats_from_cache = cache.get(settings.USER_STATS_CACHE_KEY.format(self.user_id), None)
        if stats_from_cache is None:
            stats_from_cache = {
                "num_packs": self.num_packs,
                "total_uploaded_sounds_length": self.get_total_uploaded_sounds_length(),
                "avg_rating_0_5": self.avg_rating_0_5,
            }
            cache.set(settings.USER_STATS_CACHE_KEY.format(self.user_id), stats_from_cache, 60 * 60 * 24)
        stats_from_db.update(stats_from_cache)
        return stats_from_db

    def get_ai_preference(self):
        try:
            return self.user.ai_preference.preference
        except AIPreference.DoesNotExist:
            # If no preference is set, return the default one
            return AIPreference.DEFAULT_AI_PREFERENCE

    def set_ai_preference(self, preference_value):
        num_updated = AIPreference.objects.update(user=self.user, preference=preference_value)
        if num_updated == 0:
            # If no AIPreference object was updated, it means no AIPreference object exister for that user. Create a new one.
            AIPreference.objects.create(user=self.user, preference=preference_value)

    class Meta:
        ordering = ("-user__date_joined",)
        permissions = (("can_beta_test", "Show beta features to that user."),)


class GdprAcceptance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Automatically add the date because the presence of this field means that
    # the user accepted the terms
    date_accepted = models.DateTimeField(auto_now_add=True)


class AIPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="ai_preference")
    date_updated = models.DateTimeField(auto_now=True)
    AI_PREFERENCE_CHOICES = (
        (
            "fr",
            "My sounds are used following Freesound's recommendations for interpreting Creative Commons licenses in a generative AI training context",
        ),
        ("o", "My sounds are used to train open models that are freely available to the public"),
        (
            "on",
            "My sounds are used to train open models that are freely available to the public and that do not allow a commercial use",
        ),
    )
    DEFAULT_AI_PREFERENCE = "fr"
    preference = models.CharField(max_length=2, choices=AI_PREFERENCE_CHOICES, default=DEFAULT_AI_PREFERENCE)


class UserFlag(models.Model):
    user = models.ForeignKey(User, related_name="flags", on_delete=models.CASCADE)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True)
    content_object = fields.GenericForeignKey("content_type", "object_id")
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return f"Flag {self.content_type}: {self.object_id}"

    class Meta:
        ordering = ("-user__username",)


class SameUser(models.Model):
    # Used for merging more than one user account which have the same email address

    # The main user is defined as the one who has logged in most recently
    # when we performed the migration. This is an arbitrary decision
    main_user = models.ForeignKey(User, related_name="+", on_delete=models.CASCADE)
    main_orig_email = models.CharField(max_length=200)
    secondary_user = models.ForeignKey(User, related_name="+", on_delete=models.CASCADE)
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
        return self.main_user.email.lower() != self.main_trans_email.lower()

    def secondary_user_changed_email(self):
        return self.secondary_user.email.lower() != self.secondary_trans_email.lower()


def create_user_profile(sender, instance, created, **kwargs):
    if not hasattr(instance, "profile"):
        profile = Profile.objects.create(user=instance, accepted_tos=True)
        profile.agree_to_gdpr()


post_save.connect(create_user_profile, sender=User)


def presave_user(sender, instance, **kwargs):
    try:
        old_user_object = User.objects.get(pk=instance.id)

        # Check if username has changed and, if so, create a OldUsername object (if does not exist)
        old_username = old_user_object.username
        if old_username.lower() != instance.username.lower():
            # We use .get_or_create below to avoid having 2 OldUsername objects with the same user/username pair
            OldUsername.objects.get_or_create(user=instance, username=old_username)

            # Also mark all sounds as index dirty because they'll need to be re-indexed with the new username
            Sound.objects.filter(user=instance).update(is_index_dirty=True)

        # Check if email has change and, if so, remove existing EmailBounce objects associated to the user (if any)
        old_email = old_user_object.email
        if old_email != instance.email:
            EmailBounce.objects.filter(user=instance).delete()

    except User.DoesNotExist:
        pass


pre_save.connect(presave_user, sender=User)


class EmailPreferenceType(models.Model):
    description = models.TextField(max_length=1024, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    send_by_default = models.BooleanField(
        default=True,
        help_text="Indicates if the user should receive an email, if "
        + "UserEmailSetting exists for the user then the behavior is the opposite",
    )

    def __str__(self):
        return self.display_name


class UserEmailSetting(models.Model):
    user = models.ForeignKey(User, related_name="email_settings", on_delete=models.CASCADE)
    email_type = models.ForeignKey(EmailPreferenceType, on_delete=models.CASCADE)


class OldUsername(models.Model):
    user = models.ForeignKey(User, related_name="old_usernames", on_delete=models.CASCADE)
    username = models.CharField(max_length=255, db_index=True, unique=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} > {self.user.username}"


class EmailBounce(models.Model):
    user = models.ForeignKey(User, related_name="email_bounces", on_delete=models.CASCADE)

    # Bounce types
    UNDETERMINED = "UD"
    PERMANENT = "PE"
    TRANSIENT = "TR"
    TYPE_CHOICES = ((UNDETERMINED, "Undetermined"), (PERMANENT, "Permanent"), (TRANSIENT, "Transient"))
    TYPES_INVALID = [UNDETERMINED, PERMANENT]
    type = models.CharField(db_index=True, max_length=2, choices=TYPE_CHOICES, default=UNDETERMINED)
    type_map = {t[1]: t[0] for t in TYPE_CHOICES}

    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-timestamp",)
        unique_together = ("user", "type", "timestamp")

    @classmethod
    def type_from_string(cls, value):
        return cls.type_map.get(value, cls.UNDETERMINED)


class UserDeletionRequest(models.Model):
    """
    This model is used to store information about the process of deleting Freesound user accounts.
    This was designed to handle the case when a user requests to be deleted via email and we need to track the
    whole process for GDPR compliance. However, it is also used for users who decide to delete their accounts
    via the website form and for users deleted by Freesound admins. When a user requests to be deleted via email,
    we should manually create a UserDeletionRequest object using the Freesound admin interface and manage it
    from there. Once we actually call the delete function through the admin or through some other method, the status
    of this object will be automatically changed to 'User has been deleted or anonymized', and a DeletedUser
    object containing some information about the DeletedUser (for GDPR compliance) is also created and linked to this
    UserDeletionRequest request object. The UserDeletionRequest objects can be used in a management command
    to double check that users that should have been deleted/anonymized have in fact been deleted/anonymized.
    We can do that by making sure that all UserDeletionRequest with status 'Deletion action was triggered'
    have the UserDeletionRequest.user field set to null or pointing to a User object with
    User.profile.is_anonymized_user=True.

    Description of most important fields:

    email_from = email through which the deletion request was made (used for classic GDPR case)
    user_from = user object who requested the deletion of 'user_to' (can be blank if request was done via email and
        there is no user associated with that email)
    username_from = username of 'user_from' (stored as string to better keep records in case 'user_from' gets deleted)
    user_to = user object that will be deleted (can be the same as user_from in case of self-deletion)
    username_to = username of 'user_to' (stored as string to better keep records in case 'user_from' gets deleted)
    deleted_user = DeletedUser object after 'user_to' gets deleted

    NOTE: username_from and username_to are filled in automatically when UserDeletionRequest object is saved.
    """

    email_from = models.CharField(
        max_length=200, help_text="The email from which the user deletion requestwas received."
    )
    user_from = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="deletion_requests_from", blank=True
    )
    username_from = models.CharField(max_length=150, null=True, blank=True)
    user_to = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="deletion_requests_to",
        help_text="The user account that should be deleted if this request proceeds. "
        "Note that you can click on the magnifying glass icon and search by email.",
    )
    username_to = models.CharField(max_length=150, null=True, blank=True)
    deleted_user = models.ForeignKey(DeletedUser, null=True, on_delete=models.SET_NULL)
    DELETION_REQUEST_STATUS_RECEIVED_REQUEST = "re"
    DELETION_REQUEST_STATUS_WAITING_FOR_USER = "wa"
    DELETION_REQUEST_STATUS_DELETION_CANCELLED = "ca"
    DELETION_REQUEST_STATUS_DELETION_TRIGGERED = "tr"
    DELETION_REQUEST_STATUS_USER_WAS_DELETED = "de"
    DELETION_REQUEST_STATUSES = (
        (DELETION_REQUEST_STATUS_RECEIVED_REQUEST, "Received email deletion request"),
        (DELETION_REQUEST_STATUS_WAITING_FOR_USER, "Waiting for user action"),
        (DELETION_REQUEST_STATUS_DELETION_CANCELLED, "Request was cancelled"),
        (DELETION_REQUEST_STATUS_DELETION_TRIGGERED, "Deletion action was triggered"),
        (DELETION_REQUEST_STATUS_USER_WAS_DELETED, "User has been deleted or anonymized"),
    )
    status = models.CharField(max_length=2, choices=DELETION_REQUEST_STATUSES, db_index=True, default="re")
    last_updated = models.DateTimeField(auto_now=True)

    # Store history of state changes in a PG ArrayField of strings
    status_history = ArrayField(models.CharField(max_length=200), blank=True, default=list)

    # Store the deletion action and reason triggered for that user to facilitate re-triggering if need be
    triggered_deletion_action = models.CharField(max_length=100)
    triggered_deletion_reason = models.CharField(max_length=100)


@receiver(pre_save, sender=UserDeletionRequest)
def update_status_history(sender, instance, **kwargs):
    should_update_status_history = False
    try:
        old_instance = UserDeletionRequest.objects.get(id=instance.id)
        if old_instance.status != instance.status:
            should_update_status_history = True

    except UserDeletionRequest.DoesNotExist:
        # Instance was just created, add status_history record as well
        should_update_status_history = True

    if should_update_status_history:
        instance.status_history += [
            "{}: {} ({})".format(timezone.now(), instance.get_status_display(), instance.status)
        ]


@receiver(pre_save, sender=UserDeletionRequest)
def updated_status_history(sender, instance, **kwargs):
    # Automatically update the username_to field if user_to is set
    if instance.user_to is not None and not instance.user_to.profile.is_anonymized_user:
        instance.username_to = instance.user_to.username

    # Automatically update the username_from field if user_from is set
    if instance.user_from is not None and not instance.user_from.profile.is_anonymized_user:
        instance.username_from = instance.user_from.username
