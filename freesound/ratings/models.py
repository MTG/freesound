# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Rating(models.Model):
    user = models.ForeignKey(User)

    rating = models.IntegerField()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey()

    created = models.DateTimeField()

    def __unicode__(self):
        return u"%s rated %s - %s: %d" % (self.user, self.content_type, self.content_type, self.rating)


class RatingAdmin(admin.ModelAdmin):
    raw_id_fields = ('user')
    list_display = ('user', 'content_object', 'rating', 'created')
admin.site.register(Rating, RatingAdmin)