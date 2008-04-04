# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class DaoComment(models.Model, DaoDeletePermission):
    user = models.ForeignKey(User) 

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey()

    comment = models.TextField()

    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies') 

    created = models.DateTimeField()