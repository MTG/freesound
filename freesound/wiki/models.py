# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode

class Page(models.Model):
    name = models.CharField(max_length=256, db_index=True)

    def __unicode__(self):
        return self.name

    def content(self):
        return Content.objects.filter(page=self).latest()
    
    @models.permalink
    def get_absolute_url(self):
        return ("wiki-page", (smart_unicode(self.name),))


class Content(models.Model):
    page = models.ForeignKey(Page)
    author = models.ForeignKey(User, null=True, blank=True, default=None)
    title = models.CharField(max_length=250)
    body = models.TextField()
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    class Meta:
        ordering = ('-created', )
        get_latest_by = 'created'

    def __unicode__(self):
        return self.title