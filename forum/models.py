# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import OrderedModel
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Forum(OrderedModel):

    name = models.CharField(max_length=50)
    name_slug = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=250)

    num_threads = models.PositiveIntegerField(default=0)
    num_posts = models.PositiveIntegerField(default=0)

    last_post = models.OneToOneField('Post', null=True, blank=True, default=None, related_name="latest_in_forum",
                                     on_delete=models.SET_NULL)

    def set_last_post(self):
        qs = Post.objects.filter(thread__forum=self).order_by('-created')
        if qs.count() > 0:
            self.last_post = qs[0]
            self.save()

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ("forums-forum", (smart_unicode(self.name_slug),))


class Thread(models.Model):
    forum = models.ForeignKey(Forum)
    author = models.ForeignKey(User)
    title = models.CharField(max_length=250)

    THREAD_STATUS_CHOICES = (
        (0, "Sunk"),
        (1, "Regular"),
        (2, "Sticky"),
    )
    status = models.PositiveSmallIntegerField(choices=THREAD_STATUS_CHOICES, default=1)

    num_posts = models.PositiveIntegerField(default=0)
    last_post = models.OneToOneField('Post', null=True, blank=True, default=None, related_name="latest_in_thread",
                                     on_delete=models.SET_NULL)

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def set_last_post(self):
        qs = Post.objects.filter(thread=self).order_by('-created')
        if qs.count() > 0:
            self.last_post = qs[0]
            self.save()
        self.forum.set_last_post()

    @models.permalink
    def get_absolute_url(self):
        return ("forums-thread", (smart_unicode(self.forum.name_slug), self.id))

    class Meta:
        ordering = ('-status', '-last_post__created')

    def __unicode__(self):
        return self.title


class Post(models.Model):
    thread = models.ForeignKey(Thread)
    author = models.ForeignKey(User)
    body = models.TextField()

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('created',)

    def __unicode__(self):
        return u"Post by %s in %s" % (self.author, self.thread)

    @models.permalink
    def get_absolute_url(self):
        return ("forums-post", (smart_unicode(self.thread.forum.name_slug), self.thread.id, self.id))

@receiver(post_delete, sender=Post)
def update_last_posts(**kwargs):
    post = kwargs['instance']
    post.thread.set_last_post()


class Subscription(models.Model):
    subscriber = models.ForeignKey(User)
    thread = models.ForeignKey(Thread)
    is_active = models.BooleanField(db_index=True, default=True)

    class Meta:
        unique_together = ("subscriber", "thread")

    def __unicode__(self):
        return u"%s subscribed to %s" % (self.subscriber, self.thread)
