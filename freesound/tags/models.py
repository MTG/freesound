# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Tag(models.Model):
    name = models.SlugField(unique=True, db_index=True, max_length=100)
    
    def __unicode__(self):
        return self.name

admin.site.register(Tag)

class TaggedItem(models.Model):
    user = models.ForeignKey(User)

    tag = models.ForeignKey(Tag)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey()

    created = models.DateTimeField()
    
    def __unicode__(self):
        return u"%s tagged %s - %s: %s" % (self.user, self.content_type, self.content_type, self.tag)

    @models.permalink
    def get_absolute_url(self):
        return ('tag', (smart_unicode(self.tag.id),))

class TaggedItemAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'content_object', 'tag', 'created')
admin.site.register(TaggedItem, TaggedItemAdmin)
