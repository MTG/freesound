# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from tags.models import TaggedItem, Tag
from utils.sql import DelayedQueryExecuter

class License(OrderedModel):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=8, db_index=True)
    summary = models.TextField()
    deed_url = models.URLField()
    legal_code_url = models.URLField()
    is_public = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class SoundManager(models.Manager):
    def latest_additions(self, num_sounds):
        return DelayedQueryExecuter("""
                select
                    username,
                    sound_id,
                    extra
                from (
                select
                    (select username from auth_user where auth_user.id = user_id) as username,
                    max(id) as sound_id,
                    max(created) as created,
                    count(*) - 1 as extra
                from
                    sounds_sound
                where
                    processing_state = 'OK' and
                    moderation_state = 'OK' and
                    created > now() - interval '1 year'
                group by
                    user_id
                ) as X order by created desc limit %d;""" % num_sounds)
    
    def random(self):
        from django.db import connection
        import random
        
        sound_count = self.filter(moderation_state="OK", processing_state="OK").count()

        if sound_count:
            offset = random.randint(0, sound_count - 1)
            cursor = connection.cursor() #@UndefinedVariable
            cursor.execute("select id from sounds_sound where processing_state = 'OK' and moderation_state = 'OK' offset %d limit 1" % offset)
            return cursor.fetchone()[0]
        else:
            return None


class PublicSoundManager(models.Manager):
    """ a class which only returns public sounds """
    def get_query_set(self):
        return super(PublicSoundManager, self).get_query_set().filter(moderation_state="OK", processing_state="OK")

class Sound(SocialModel):
    user = models.ForeignKey(User)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    # filenames
    original_filename = models.CharField(max_length=512) # name of the file the user uploaded
    original_path = models.CharField(max_length=512, null=True, blank=True, default=None) # name of the file on disk before processing
    base_filename_slug = models.CharField(max_length=512, null=True, blank=True, default=None) # base of the filename, this will be something like: id__username__filenameslug
   
    # user defined fields
    description = models.TextField()
    date_recorded = models.DateField(null=True, blank=True, default=None)

    license = models.ForeignKey(License)
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    
    # file properties
    SOUND_TYPE_CHOICES = (
        ('wav', 'Wave'),
        ('ogg', 'Ogg Vorbis'),
        ('aif', 'AIFF'),
        ('mp3', 'Mp3'),
        ('flac', 'Flac')
    )
    type = models.CharField(db_index=True, max_length=4, choices=SOUND_TYPE_CHOICES)
    duration = models.FloatField(default=0)
    bitrate = models.IntegerField(default=0)
    bitdepth = models.IntegerField(null=True, blank=True, default=None)
    samplerate = models.FloatField(default=0)
    filesize = models.IntegerField(default=0)
    channels = models.IntegerField(default=0)
    md5 = models.CharField(max_length=32, unique=True, db_index=True)
    
    # moderation
    MODERATION_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("DE",_('Deferred')),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)
    moderation_note = models.TextField(null=True, blank=True, default=None)
    has_bad_description = models.BooleanField(default=False)
    
    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("FA",_('Failed')),
    )
    processing_state = models.CharField(db_index=True, max_length=2, choices=PROCESSING_STATE_CHOICES, default="PE")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)
    processing_log = models.TextField(null=True, blank=True, default=None)
    
    num_comments = models.PositiveIntegerField(default=0)
    num_downloads = models.PositiveIntegerField(default=0)
    
    avg_rating = models.FloatField(default=0)
    num_ratings = models.PositiveIntegerField(default=0)
    
    objects = SoundManager()
    public = PublicSoundManager()
    
    def __unicode__(self):
        return u"%s by %s" % (self.base_filename_slug, self.user)
    
    def paths(self):
        if hasattr(self, '_paths_cache'):
            return self._paths_cache

        id_folder = self.id/1000
        
        sound_folder = u"%d/sounds/" % id_folder
        sound_base = u"%s.%s" % (self.base_filename_slug, self.type)
        sound_path = sound_folder + sound_base 
        
        preview_folder = u"%d/previews/" % id_folder
        preview_base = u"%s.mp3" % self.base_filename_slug
        preview_path = preview_folder + preview_base
        
        waveform_folder = preview_folder
        waveform_base_m = u"%s_m.png" % self.base_filename_slug
        waveform_path_m = waveform_folder + waveform_base_m
        waveform_base_l = u"%s_l.png" % self.base_filename_slug
        waveform_path_l = waveform_folder + waveform_base_l
        
        spectral_folder = preview_folder
        spectral_base_m = u"%s_m.jpg" % self.base_filename_slug
        spectral_path_m = spectral_folder + spectral_base_m
        spectral_base_l = u"%s_l.jpg" % self.base_filename_slug
        spectral_path_l = spectral_folder + spectral_base_l
        
        paths = locals().copy()
        paths.pop("self")
        paths.pop("id_folder")
        
        self._paths_cache = paths

        return paths

    def get_channels_display(self):
        if self.channels == 1:
            return u"Mono" 
        elif self.channels == 2:
            return u"Stereo" 
        else:
            return self.channels
    
    def type_warning(self):
        return self.type == "ogg" or self.type == "flac" 
    
    def duration_warning(self):
        # warn from 5 minutes and more
        return self.duration > 60*5
    
    def filesize_warning(self):
        # warn for 50MB and up
        return self.filesize > 50 * 1024 * 1024

    def samplerate_warning(self):
        # warn anything special
        return self.samplerate not in [11025, 22050, 44100]
    
    def bitdepth_warning(self):
        return self.bitdepth not in [8,16]
        
    def bitrate_warning(self):
        return self.bitrate not in [32, 64, 96, 128, 160, 192, 224, 256, 320]

    def channels_warning(self):
        return self.channels not in [1,2]
    
    def duration_ms(self):
        return self.duration * 1000
    
    def rating_percent(self):
        return int(self.avg_rating*10)
    
    def process(self, force=False, do_cleanup=True):
        if force or self.processing_state != "OK":
            from utils.audioprocessing.freesound_audio_processing import process
            return process(self, do_cleanup)
        else:
            return True
            
    def add_to_search_index(self):
        from utils.search.search import add_sound_to_solr
        add_sound_to_solr(self)

    @models.permalink
    def get_absolute_url(self):
        return ('sound', (self.user.username, smart_unicode(self.id),))
    
    def set_tags(self, tags):
        # remove tags that are not in the list
        for tagged_item in self.tags.all():
            if tagged_item.tag.name not in tags:
                tagged_item.delete()

        # add tags that are not there yet
        for tag in tags:
            if self.tags.filter(tag__name=tag).count() == 0:
                (tag_object, created) = Tag.objects.get_or_create(name=tag) #@UnusedVariable
                tagged_object = TaggedItem.objects.create(user=self.user, tag=tag_object, content_object=self)
                tagged_object.save()
    
    class Meta(SocialModel.Meta):
        ordering = ("-created", )


class Pack(SocialModel):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)
    name_slug = models.SlugField(max_length=255, db_index=True)
    
    description = models.TextField(null=True, blank=True, default=None)

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    num_downloads = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return u"%s by %s" % (self.name, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('pack', (smart_unicode(self.id),))    
    
    class Meta(SocialModel.Meta):
        unique_together = ('user', 'name')
        ordering = ("-created",)


class Flag(models.Model):
    sound = models.ForeignKey(Sound)
    reporting_user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField()
    REASON_TYPE_CHOICES = (
        ("O",_('Offending sound')),
        ("I",_('Illegal sound')),
        ("T",_('Other problem')),
    )
    reason_type = models.CharField(max_length=1, choices=REASON_TYPE_CHOICES, default="I")
    reason = models.TextField()
    
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __unicode__(self):
        return u"%s: %s" % (self.reason_type, self.reason[:100])
    
    class Meta:
        ordering = ("-created",)


class Download(models.Model):
    user = models.ForeignKey(User)
    sound = models.ForeignKey(Sound, null=True, blank=True, default=None)
    pack = models.ForeignKey(Pack, null=True, blank=True, default=None)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    class Meta:
        ordering = ("-created",)