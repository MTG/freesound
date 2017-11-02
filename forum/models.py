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
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils.encoding import smart_unicode
from general.models import OrderedModel
from django.db.models.signals import post_delete, pre_delete, pre_save, post_save
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

    def set_last_post(self, commit=True):
        qs = Post.objects.filter(thread__forum=self,moderation_state ='OK')
#        if exclude_post:
#            qs = qs.exclude(id=exclude_post.id)
#        if exclude_thread:
#            qs = qs.exclude(thread=exclude_thread)
        qs = qs.order_by('-created')
        if qs.count() > 0:
            self.last_post = qs[0]
        else:
            self.last_post = None
        if commit:
            self.save()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("forums-forum", args=[smart_unicode(self.name_slug)])

    def get_last_post(self):
        return Post.objects.filter(thread__forum=self,moderation_state ='OK').order_by("-created")[0]


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


@receiver(post_save, sender=Thread)
def update_num_threads_on_thread_insert(**kwargs):
    thread = kwargs['instance']
    if kwargs['created']:
        thread.forum.num_threads = F('num_threads') + 1
        thread.forum.save()


@receiver(pre_save, sender=Thread)
def update_num_threads_on_thread_update(sender, instance, **kwargs):
    if instance.id:
        with transaction.atomic():
            old_thread = Thread.objects.get(pk=instance.id)
            if old_thread.forum_id != instance.forum_id:
                old_thread.forum.num_threads = F('num_threads') - 1
                old_thread.forum.save()
                instance.forum.num_threads = F('num_threads') + 1
                instance.forum.save()


@receiver(post_delete, sender=Thread)
def update_last_post_on_thread_delete(**kwargs):
    thread = kwargs['instance']
    try:
        with transaction.atomic():
            thread.forum.refresh_from_db()
            thread.forum.num_threads = F('num_threads') - 1
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


@receiver(post_save, sender=Post)
def update_num_posts_on_post_insert(**kwargs):
    if kwargs['created']:
        post = kwargs['instance']
        post.author.profile.num_posts = F('num_posts') + 1
        post.author.profile.save()
        # The method set_last_post from Thread calls the method set_last_post from Forum.
        # The save of the forum instance is done in set_last_post from Forum class.
        # So is important to keep the order of this lines
        post.thread.forum.num_posts = F('num_posts') + 1
        post.thread.set_last_post()
        post.thread.num_posts = F('num_posts') + 1
        post.thread.save()
        invalidate_template_cache('latest_posts')


@receiver(post_delete, sender=Post)
def update_last_post_on_post_delete(**kwargs):
    post = kwargs['instance']
    delete_post_from_solr(post)
    try:
        post.thread.forum.num_posts = F('num_posts') - 1
        post.thread.forum.save()
        post.author.profile.num_posts = F('num_posts') - 1
        post.author.profile.save()
        post.thread.forum.refresh_from_db()
        post.thread.set_last_post()
        post.thread.refresh_from_db()
        if post.thread:
            post.thread.num_posts = F('num_posts') - 1
            post.thread.save()
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
