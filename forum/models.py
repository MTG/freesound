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

    def set_last_post(self):
        """
        Set the `last_post` field of this forum to be the most recently
        written OK moderated Post.
        This does not save the current Forum object.
        """
        qs = Post.objects.filter(thread__forum=self, moderation_state='OK')
        qs = qs.order_by('-created')
        if qs.exists():
            self.last_post = qs[0]
        else:
            self.last_post = None

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
        qs = Post.objects.filter(thread=self)
        has_posts = qs.exists()
        moderated_posts = qs.filter(moderation_state='OK').order_by('-created')
        if moderated_posts.count() > 0:
            self.last_post = moderated_posts[0]
        else:
            self.last_post = None

        return has_posts

    def get_absolute_url(self):
        return reverse("forums-thread", args=[smart_unicode(self.forum.name_slug), self.id])

    class Meta:
        ordering = ('-status', '-last_post__created')

    def __unicode__(self):
        return self.title


@receiver(post_save, sender=Thread)
def update_num_threads_on_thread_insert(sender, instance, created, **kwargs):
    """Increase the number of threads when a new thread is created in a Forum."""
    thread = instance
    if created:
        thread.forum.num_threads = F('num_threads') + 1
        thread.forum.save()


@receiver(pre_save, sender=Thread)
def update_num_threads_on_thread_update(sender, instance, **kwargs):
    """If a thread is moved from one forum to another, adjust
    `num_threads` for each of the two forums.
    """
    if instance.id:
        with transaction.atomic():
            old_thread = Thread.objects.get(pk=instance.id)
            if old_thread.forum_id != instance.forum_id:
                old_thread.forum.num_threads = F('num_threads') - 1
                old_thread.forum.save()
                instance.forum.num_threads = F('num_threads') + 1
                instance.forum.save()


@receiver(post_delete, sender=Thread)
def update_last_post_on_thread_delete(sender, instance, **kwargs):
    """If a thread is deleted, update num_threads on the forum and update the
    Forum's last_post (if needed)"""
    thread = instance
    try:
        with transaction.atomic():
            thread.forum.refresh_from_db()
            thread.forum.num_threads = F('num_threads') - 1
            thread.forum.set_last_post()
            thread.forum.save()
    except Forum.DoesNotExist:
        pass


class Post(models.Model):
    thread = models.ForeignKey(Thread)
    author = models.ForeignKey(User, related_name='posts')
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


@receiver(pre_save, sender=Post)
def update_num_posts_on_save_if_moderation_changes(sender, instance, **kwargs):
    """If the moderation state of a post changed to or from OK, update counts."""
    post = instance
    if post.pk:
        with transaction.atomic():
            old = Post.objects.get(pk=post.pk)
            change = 0
            if old.moderation_state == 'NM' and instance.moderation_state == 'OK':
                change = 1
            elif old.moderation_state == 'OK' and instance.moderation_state == 'NM':
                change = -1
            if change != 0:
                post.author.profile.num_posts = F('num_posts') + change
                post.author.profile.save()
                post.thread.forum.num_posts = F('num_posts') + change
                post.thread.forum.save(update_fields=['num_posts'])
                post.thread.num_posts = F('num_posts') + change
                post.thread.save(update_fields=['num_posts'])


@receiver(post_save, sender=Post)
def update_num_posts_on_post_insert(sender, instance, created, **kwargs):
    """Increase num_posts and set last_post when a new Post is created"""
    post = instance
    if created and post.moderation_state == "OK":
        with transaction.atomic():
            post.author.profile.num_posts = F('num_posts') + 1
            post.author.profile.save()
            post.thread.forum.num_posts = F('num_posts') + 1
            post.thread.forum.last_post = post
            post.thread.forum.save()
            post.thread.num_posts = F('num_posts') + 1
            post.thread.last_post = post
            post.thread.save()
        invalidate_template_cache('latest_posts')
    elif not created and post.moderation_state == "OK":
        post.thread.forum.set_last_post()
        post.thread.forum.save(update_fields=['last_post'])
        post.thread.set_last_post()
        post.thread.save(update_fields=['last_post'])


@receiver(post_delete, sender=Post)
def update_last_post_on_post_delete(sender, instance, **kwargs):
    """Update num_posts counts and last_post pointers when a Post is deleted.

    Reduce num_posts by 1 for the author, forum, and thread
    Set last_post for the forum
    Set last_post for the thread. If this was the only remaining post
    in the thread and it was deleted, also delete the thread.

    If the post was not moderated, don't update the values
    """
    post = instance
    delete_post_from_solr(post)
    if post.moderation_state == "OK":
        try:
            with transaction.atomic():
                post.author.profile.num_posts = F('num_posts') - 1
                post.author.profile.save()
                post.thread.forum.refresh_from_db()
                post.thread.forum.num_posts = F('num_posts') - 1
                post.thread.forum.set_last_post()
                post.thread.forum.save()
                thread_has_posts = post.thread.set_last_post()
                if thread_has_posts:
                    post.thread.num_posts = F('num_posts') - 1
                    post.thread.save()
                else:
                    post.thread.delete()
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
