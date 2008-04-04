# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Tag(models.Model):
    name = models.SlugField(unique=True, db_index=True, max_length=100)

class TaggedItem(models.Model):
    tag = models.ForeignKey(Tag)

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_field=True)
    content_object = generic.GenericForeignKey()

    user = models.ForeignKey(User)
    created = models.DateTimeField()