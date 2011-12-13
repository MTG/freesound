# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from sounds.models import Sound
from django.db import models

class Bookmark(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128, default="")
    # add constraint name unique
    sound = models.ForeignKey(Sound)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __unicode__(self):
        return u"%s bookmarks sound %s" % (self.user, self.sound.id)
    
    class Meta:
        unique_together = (('user', 'sound'),)
        ordering = ("-created", )


class BookmarkCategory(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128)
    bookmarks = models.ManyToManyField(Bookmark, related_name='categories', blank=True)
    description = models.TextField(null=True, blank=True, default=None)
    
    def __unicode__(self):
        return u"Bookmark category: %s" % (self.name)