# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

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


class GeoTagAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'lat', 'lon', 'created')

admin.site.register(GeoTag, GeoTagAdmin)