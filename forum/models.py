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
from django.urls import reverse
from django.utils.encoding import smart_unicode
from general.models import OrderedModel
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from utils.cache import invalidate_template_cache
from django.utils.translation import ugettext as _
from utils.search.search_forum import delete_post_from_solr
import logging

logger = logging.getLogger('web')

class Forum(OrderedModel):

    name = models.CharField(max_length=50)
    name_slug = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=250)

    num_threads = models.PositiveIntegerField(default=0)
    num_posts = models.PositiveIntegerField(default=0)

    last_post = models.OneToOneField('Post', null=True, blank=True, default=None,
                                     related_name="latest_in_forum",
                                     on_delete=models.SET_NULL)

    def set_last_post(self):
        qs = Post.objects.filter(thread__forum=self,moderation_state ='OK')
        qs = qs.order_by('-created')
        if qs.count() > 0:
            self.last_post = qs[0]
            self.save()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("forums-forum", args=[smart_unicode(self.name_slug)])


class Thread(models.Model):
    forum = models.ForeignKey(Forum)
    author = models.ForeignKey(User)
    title = models.CharField(max_length=250)

    THREAD_STATUS_CHOICES = (
        (0, "Sunk"),
        (1, "Regular"),
        (2, "Sticky"),
    )
    status = models.PositiveSmallIntegerField(choices=THREAD_STATUS_CHOICES, default=1, db_index=True)

    num_posts = models.PositiveIntegerField(default=0)
    last_post = models.OneToOneField('Post', null=True, blank=True, default=None,
                                     related_name="latest_in_thread",
                                     on_delete=models.SET_NULL)
    first_post = models.OneToOneField('Post', null=True, blank=True, default=None,
                                      related_name="first_in_thread",
                                      on_delete=models.SET_NULL)

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def set_last_post(self):
        qs = Post.objects.filter(thread=self).order_by('-created')
        if qs.count() > 0:
            self.last_post = qs[0]
            self.save()
            try:
                self.forum.set_last_post()
            except Forum.DoesNotExist:
                pass
        else:
            self.delete()

    def get_absolute_url(self):
        return reverse("forums-thread", args=[smart_unicode(self.forum.name_slug), self.id])

    class Meta:
        ordering = ('-status', '-last_post__created')

    def __unicode__(self):
        return self.title


@receiver(post_delete, sender=Thread)
def update_last_post_on_thread_delete(**kwargs):
    thread = kwargs['instance']
    try:
        thread.forum.set_last_post()
    except Forum.DoesNotExist:
        pass


class Post(models.Model):
    thread = models.ForeignKey(Thread)
    author = models.ForeignKey(User)
    body = models.TextField()

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    MODERATION_STATE_CHOICES = (
        ("NM",_('NEEDS_MODERATION')),
        ("OK",_('OK')),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="OK")

    class Meta:
        ordering = ('created',)
        permissions = (
            ("can_moderate_forum", "Can moderate posts."),
        )

    def __unicode__(self):
        return u"Post by %s in %s" % (self.author, self.thread)

    def get_absolute_url(self):
        return reverse("forums-post", args=[smart_unicode(self.thread.forum.name_slug), self.thread.id, self.id])


@receiver(post_delete, sender=Post)
def update_last_post_on_post_delete(**kwargs):
    post = kwargs['instance']
    delete_post_from_solr(post)
    try:
        post.thread.set_last_post()
    except Thread.DoesNotExist:
        # This happens when the thread has already been deleted, for example
        # when a user is deleted through the admin interface. We don't need
        # to update the thread, but it would be nice to get to the forum object
        # somehow and update that one....
        logger.info('Tried setting last posts for thread and forum, but the thread has already been deleted?')
    invalidate_template_cache('latest_posts')


class Subscription(models.Model):
    subscriber = models.ForeignKey(User)
    thread = models.ForeignKey(Thread)
    is_active = models.BooleanField(db_index=True, default=True)

    class Meta:
        unique_together = ("subscriber", "thread")

    def __unicode__(self):
        return u"%s subscribed to %s" % (self.subscriber, self.thread)
