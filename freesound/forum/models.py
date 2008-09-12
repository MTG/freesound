# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import OrderedModel
from django.conf import settings

class Category(OrderedModel):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name
   

class Forum(OrderedModel):
    category = models.ForeignKey(Category)
    
    name = models.CharField(max_length=50)
    name_slug = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=250)

    num_threads = models.PositiveIntegerField(default=0)
    num_views = models.PositiveIntegerField(default=0)
    last_post = models.OneToOneField('Post', null=True, blank=True, default=None, related_name="latest_in_forum")

    def __unicode__(self):
        return self.name
    
    @models.permalink
    def get_absolute_url(self):
        return ("forum", (smart_unicode(self.name_slug),))


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
    
    num_posts = models.PositiveIntegerField(default=1)
    num_views = models.PositiveIntegerField(default=0)
    last_post = models.OneToOneField('Post', null=True, blank=True, default=None, related_name="latest_in_thread")

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    class Meta:
        ordering = ('-status', '-created')

    def __unicode__(self):
        return self.title
    
    def save(self):
        super(Thread, self).save()
        f = self.forum
        f.num_threads = Thread.objects.filter(forum=self.forum).count()
        f.save()

    @models.permalink
    def get_absolute_url(self):
        return ("thread", (smart_unicode(self.forum.name_slug), smart_unicode(self.id)))


class Post(models.Model):
    thread = models.ForeignKey(Thread)
    author = models.ForeignKey(User)
    body = models.TextField()
    
    num_views = models.PositiveIntegerField(default=0)
    
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return u"Post by %s in %s" % (self.author, self.thread)

    def save(self):
        super(Post, self).save()

        t = self.thread
        t.num_posts = Post.objects.filter(thread=self.thread).count()
        t.last_post = self
        t.save()
        
        f = self.thread.forum
        f.last_post = self
        f.save()
        
    def get_absolute_url(self):
        posts_before = Post.objects.filter(thread=self.thread, created__lt=self.created).count()
        page = 1 + posts_before / settings.FORUM_POSTS_PER_PAGE
        return self.thread.get_absolute_url() + "?page=%d#post%d" % (page, self.id)


class Subscription(models.Model):
    author = models.ForeignKey(User)
    thread = models.ForeignKey(Thread)
    active = models.BooleanField(db_index=True, default=True)
    
    class Meta:
        unique_together = ("author", "thread")
        
    def __unicode__(self):
        return u"%s subscribed to %s" % (self.author, self.thread)

    # A
    # B > notify A, set Subscription passive
    # C > notify B, set subscription passive
    # B comes to see > set subscription acive
    # D > notify B