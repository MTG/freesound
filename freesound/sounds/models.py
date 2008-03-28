# -*- coding: utf-8 -*-

from datetime import datetime
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

class Sound(models.Model):
    user = models.ForeignKey(User, raw_id_admin=True)
    type = models.CharField(max_length=512)
    title = models.CharField(max_length=512)
    title_slug = models.CharField(max_length=600)
    description = models.TextField()
    
    pack = models.ForeignKey(null=True, blank=True)
    sources =  models.ManyToManyField('self', symmetrical=False, related_name='remixes')
    
    
    
    created = models.DateTimeField()
    modified = models.DateTimeField()

class SoundPack(models.Model):
    user = models.ForeignKey(User=True)
    name = models.CharField(max_length=255)
    name_slug = models.SlugField(max_length=255) # slug from title
    
    created = models.DateTimeField()
    modified = models.DateTimeField()