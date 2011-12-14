# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from sounds.models import Sound
from django.db import models

class BookmarkCategory(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128, default ="")
    
    def __unicode__(self):
        return u"Bookmark category: %s" % (self.name)

class Bookmark(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128, default="")
    # When deleting a category, should we delete all the bookmarks inside?
    # For the moment I use the default behavior which is deleting them (CASCADE). It could be avoided using on_delete=models.SET_NULL
    # The reason to delete the bookmark is that it makes no sense to send it to "uncategorized" if then you cannot edit the category
    category = models.ForeignKey(BookmarkCategory, blank = True, null = True, default = None, related_name='bookmarks')
    sound = models.ForeignKey(Sound)
    created = models.DateTimeField(db_index = True, auto_now_add = True)
    
    def __unicode__(self):
        return u"Bookmark: %s" % (self.name)
    
    class Meta:
        ordering = ("-created", )


