# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import smart_unicode

class GeoTag(models.Model):
    user = models.ForeignKey(User)

    lat = models.FloatField(db_index=True)
    lon = models.FloatField(db_index=True)
    zoom = models.IntegerField(db_index=True)

    created = models.DateTimeField()
    
    def __unicode__(self):
        return u"(%f,%f)" % (self.lat, self.lon)

    @models.permalink
    def get_absolute_url(self):
        return ('geotag', (smart_unicode(self.id),))