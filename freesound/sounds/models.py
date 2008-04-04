# -*- coding: utf-8 -*-

from datetime import datetime
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

class License(models.Model):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=5)
    summary = models.TextField()
    deed_url = models.URLField()
    legal_code_url = models.URLField()


class Sound(models.Model):
    user = models.ForeignKey(User, raw_id_admin=True)
    
    license = models.ForeignKey(License)
    pack = models.ForeignKey('SoundPack', null=True, blank=True)
    sources =  models.ManyToManyField('self', symmetrical=False, related_name='remixes')

    filename_base = models.CharField(max_length=512) # original filename without extension
    filename_slug = models.CharField(max_length=512, db_index=True)
    description = models.TextField()
    
    # --- file properties ----------------------------------------
    SOUND_TYPE_CHOICES = (
                          ('wav', 'Wave'),
                          ('ogg', 'Ogg Vorbis'),
                          ('aif', 'AIFF'),
                          ('mp3', 'Mpeg II layer 3'),
                          ('flac', 'Flac')
                         )
    type = models.CharField(db_index=True, max_length=4, choices=SOUND_TYPE_CHOICES)

    duration = models.FloatField(default=0)
    bitrate = models.IntegerField(default=0)
    bitdepth = models.IntegerField(null=True, blank=True, default=None)
    samplerate = models.FloatField(default=0)
    filesize = models.IntegerField(default=0)
    channels = models.IntegerField(default=0)
    
    # --- moderation ----------------------------------------
    MODERATION_STATE_CHOICES = (
                                ("PE",_('Pending')),
                                ("OK",_('OK')),
                                ("DE",_('Deferred')),
                                )
    
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)
    moderation_bad_description = models.BooleanField(default=False)
    
    # --- processing ----------------------------------------
    PROCESSING_STATE_CHOICES = (
                                ("PE",_('Pending')),
                                ("OK",_('OK')),
                                ("FA",_('Failed')),
                                )
    
    processing_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)
    processing_log = models.TextField(null=True, blank=True, default=None)
    
    created = models.DateTimeField()
    modified = models.DateTimeField()


class SoundPack(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)
    name_slug = models.SlugField(max_length=255, db_index=True)
    
    description = models.TextField()

    created = models.DateTimeField()
    modified = models.DateTimeField()
    

class SoundReport(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField(null=True, blank=True)
    reason = models.TextField()
    created = models.DateTimeField()