# -*- coding: utf-8 -*-
from django.contrib import admin
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.db import models
from django.utils.translation import ugettext as _
from general.models import SocialModel
from geotags.models import GeoTag

class License(models.Model):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=5)
    summary = models.TextField()
    deed_url = models.URLField()
    legal_code_url = models.URLField()

    def __unicode__(self):
        return self.name

class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url')

admin.site.register(License, LicenseAdmin)


class Sound(SocialModel):
    user = models.ForeignKey(User)
    created = models.DateTimeField()
    modified = models.DateTimeField()
    
    # filenames
    original_path = models.CharField(max_length=512, null=True, blank=True, default=None) # name of the file on disk before processing
    base_filename_slug = models.CharField(max_length=512) # base of the filename, this will be something like: id__username__filenameslug
   
    # user defined fields
    description = models.TextField()
    license = models.ForeignKey(License)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    original_filename = models.CharField(max_length=512) # name of the file the user uploaded
    sources =  models.ManyToManyField('self', symmetrical=False, related_name='remixes')
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None)
    
    # file properties
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
    
    # moderation
    MODERATION_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("DE",_('Deferred')),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)
    moderation_bad_description = models.BooleanField(default=False)
    
    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("FA",_('Failed')),
    )
    processing_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)
    processing_log = models.TextField(null=True, blank=True, default=None)
    
    def __unicode__(self):
        return u"%s by %s" % (self.filename_slug, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('sound', (smart_unicode(self.id),))


class SoundAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'pack', 'sources', 'geotag')
    list_display = ('user_from', 'user_to', 'subject', 'read', 'deleted', 'created')
    list_filter = ('processing_state', 'moderation_state', 'license')
    fieldsets = (
         (None, {'Fields': ('user', 'created', 'modified')}),
         ('Filenames', {'fields': ('original_path', 'base_filename_slug')}),
         ('User defined fields', {'fields': ('description', 'license', 'geotag', 'original_filename', 'sources', 'sources', 'pack')}),
         ('File properties', {'fields': ('type', 'duration', 'bitrate', 'bitdepth', 'samplerate', 'filesize', 'channels')}),
         ('Moderation', {'fields': ('moderation_state', 'moderation_date', 'moderation_bad_description')}),
         ('Processing', {'fields': ('processing_state', 'processing_date', 'processing_log')}),
     )

admin.site.register(Sound, SoundAdmin)


class Pack(SocialModel):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)
    name_slug = models.SlugField(max_length=255, db_index=True)
    
    description = models.TextField()

    created = models.DateTimeField()
    modified = models.DateTimeField()
    
    def __unicode__(self):
        return u"%s by %s" % (self.name, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('pack', (smart_unicode(self.id),))    


class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')

admin.site.register(Pack, PackAdmin)


class Report(models.Model):
    sound = models.ForeignKey(Sound)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField(null=True, blank=True)
    REASON_TYPE_CHOICES = (
        ("O",_('Offending')),
        ("I",_('Illegal')),
        ("T",_('Other')),
    )
    reason_type = models.CharField(max_length=1, choices=REASON_TYPE_CHOICES, default="T")
    reason = models.TextField()
    created = models.DateTimeField()
    
    def __unicode__(self):
        return u"%s: %s" % (self.reason_type, self.reason[:100])


class ReportAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('reporting_user', 'email', 'reason_type')

admin.site.register(Report, ReportAdmin)
