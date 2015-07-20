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
from django.db import models
from django.db.models.signals import post_save
from django.utils.encoding import smart_unicode
from general.models import SocialModel
from geotags.models import GeoTag
from utils.sql import DelayedQueryExecuter
from django.conf import settings
from utils.locations import locations_decorator
import datetime
import os
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from tickets.views import get_num_pending_sounds


class ResetEmailRequest(models.Model):
    email = models.EmailField()
    user = models.OneToOneField(User, db_index=True)
    
    
class ProfileManager(models.Manager):
    def random_uploader(self):
        import random

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

    wants_newsletter = models.BooleanField(default=True, db_index=True)
    is_whitelisted = models.BooleanField(default=False, db_index=True)

    num_sounds = models.PositiveIntegerField(editable=False, default=0)
    num_posts = models.PositiveIntegerField(editable=False, default=0)

    has_old_license = models.BooleanField(null=False, default=False)
    not_shown_in_online_users_list = models.BooleanField(null=False, default=False)

    accepted_tos = models.BooleanField(default=False)

    enabled_stream_emails = models.BooleanField(db_index=True, default=False)
    last_stream_email_sent = models.DateTimeField(db_index=True, null=True, default=None)

    objects = ProfileManager()

    def __unicode__(self):
        return self.user.username

    @models.permalink
    def get_absolute_url(self):
        return ('account', (smart_unicode(self.user.username),))

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
            avatar = dict(
                S = dict(
                    path = os.path.join(settings.AVATARS_PATH, id_folder, "%d_S.jpg" % self.user_id),
                    url = s_avatar
                ),
                M = dict(
                    path = os.path.join(settings.AVATARS_PATH, id_folder, "%d_M.jpg" % self.user_id),
                    url = m_avatar
                ),
                L = dict(
                    path = os.path.join(settings.AVATARS_PATH, id_folder, "%d_L.jpg" % self.user_id),
                    url = l_avatar
                )
            )
        )

    def get_tagcloud(self):
        return DelayedQueryExecuter("""
            select
                tags_tag.name as name,
                X.c as count
            from (
                select
                    tag_id,
                    count(*) as c
                from tags_taggeditem
                left join sounds_sound on
                    object_id=sounds_sound.id
                where
                    tags_taggeditem.user_id=%d and
                    sounds_sound.moderation_state='OK' and
                    sounds_sound.processing_state='OK'
                group by tag_id
                order by c
                desc limit 10
            ) as X
            left join tags_tag on tags_tag.id=X.tag_id
            order by tags_tag.name;""" % self.user_id)

    def can_post_in_forum(self):

        # POSTS PENDING TO MODERATE: Do not allow new posts if there are others pending to moderate
        user_has_posts_pending_to_moderate = self.user.post_set.filter(moderation_state="NM").count() > 0
        if user_has_posts_pending_to_moderate:
            return False, "We're sorry but you can't post to the forum because you have previous posts still pending to moderate"

        # THROTTLING
        if self.user.post_set.all().count() >= 1 and self.user.sounds.all().count() == 0:
            today = datetime.datetime.today()
            reference_date = self.user.post_set.all()[0].created # or since registration date: reference_date = self.user.date_joined

            # Do not allow posts if last post is not older than 5 minutes
            seconds_per_post = 60*5
            if (today - self.user.post_set.all().reverse()[0].created).seconds < seconds_per_post:
                return False, "We're sorry but you can't post to the forum because your last post was less than 5 minutes ago"

            # Do not allow posts if user has already posyted N posts that day
            # (every day users can post as many posts as twice the number of days since the reference date (registration or first post date))
            max_posts_per_day = 5 + pow((today - reference_date).days,2)
            if self.user.post_set.filter(created__range=(today-datetime.timedelta(days=1),today)).count() > max_posts_per_day:
                return False, "We're sorry but you can't post to the forum because you exceeded your maximum number of posts per day"

        return True, ""

    def is_blocked_for_spam_reports(self):
        reports_count = UserFlag.objects.filter(user__username = self.user.username).values('reporting_user').distinct().count()
        if reports_count < settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING or self.user.sounds.all().count() > 0:
            return False
        else:
            return True

    def num_sounds_pending_moderation(self):
        return get_num_pending_sounds(self.user)

    class Meta(SocialModel.Meta):
        ordering = ('-user__date_joined', )


class UserFlag(models.Model):
    user = models.ForeignKey(User, related_name="flags")
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"Flag %s: %s" % (self.content_type, self.object_id)

    class Meta:
        ordering = ("-user__username",)


def create_user_profile(sender, instance, created, **kwargs):
    try:
        instance.profile
    except Profile.DoesNotExist:
        profile = Profile(user=instance, wants_newsletter=False, accepted_tos=False)
        profile.save()

post_save.connect(create_user_profile, sender=User)