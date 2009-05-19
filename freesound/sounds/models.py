# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.db import models
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from general.models import OrderedModel, SocialModel
from geotags.models import GeoTag
from utils.sql import DelayedQueryExecuter

class License(OrderedModel):
    """A creative commons license model"""
    name = models.CharField(max_length=512)
    abbreviation = models.CharField(max_length=5, db_index=True)
    summary = models.TextField()
    deed_url = models.URLField()
    legal_code_url = models.URLField()

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
        offset = random.randint(0, self.filter(moderation_state="OK", processing_state="OK").count() - 1)
        cursor = connection.cursor()
        cursor.execute("select id from sounds_sound where processing_state = 'OK' and moderation_state = 'OK' offset %d limit 1" % offset)
        return cursor.fetchone()[0]


class Sound(SocialModel):
    user = models.ForeignKey(User)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    # filenames
    original_path = models.CharField(max_length=512, null=True, blank=True, default=None) # name of the file on disk before processing
    base_filename_slug = models.CharField(max_length=512, null=True, blank=True, default=None) # base of the filename, this will be something like: id__username__filenameslug
   
    # user defined fields
    description = models.TextField()
    license = models.ForeignKey(License)
    original_filename = models.CharField(max_length=512) # name of the file the user uploaded
    sources = models.ManyToManyField('self', symmetrical=False, related_name='remixes', blank=True)
    pack = models.ForeignKey('Pack', null=True, blank=True, default=None)
    date_recorded = models.DateField(null=True, blank=True, default=None)
    geotag = models.ForeignKey(GeoTag, null=True, blank=True, default=None)
    
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
    md5 = models.CharField(max_length=32, unique=True, db_index=True)
    
    # moderation
    MODERATION_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("DE",_('Deferred')),
    )
    moderation_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    moderation_date = models.DateTimeField(null=True, blank=True, default=None)
    has_bad_description = models.BooleanField(default=False)
    
    # processing
    PROCESSING_STATE_CHOICES = (
        ("PE",_('Pending')),
        ("OK",_('OK')),
        ("FA",_('Failed')),
    )
    processing_state = models.CharField(db_index=True, max_length=2, choices=MODERATION_STATE_CHOICES, default="PE")
    processing_date = models.DateTimeField(null=True, blank=True, default=None)
    processing_log = models.TextField(null=True, blank=True, default=None)
    
    num_comments = models.IntegerField(default=0)
    num_downloads = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0)
    
    objects = SoundManager()
    
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
        return self.duration > 60
    
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
    
    def process(self, force=False):
        if force or self.processing_state != "OK":
            from utils.text import slugify
            import tempfile, os.path, os
            import utils.audioprocessing.processing as audioprocessing
            from utils.filesystem import md5file
            
            def fail(message, error=None):
                self.processing_log += "--FAIL---------\n" + message + "\n"
                if error:
                    self.processing_log += str(error) + "\n----------\n"
                self.processing_state = "FA"
                self.save()
                
            def win(message):
                self.processing_log += "--WIN----------\n" + message + "\n"
            
            def cleanup(files):
                for filename in files:
                    try:
                        os.unlink(filename)
                    except:
                        pass
            
            # only keep the last processing attempt
            self.processing_log = "" 
            self.processing_date = datetime.now()
            original_filename = os.path.splitext(os.path.basename(self.original_filename))[0]
            self.base_filename_slug = "%d__%s__%s" % (self.id, slugify(self.user.username), slugify(original_filename))
            self.save()
            paths = self.paths()

            if not os.path.exists(self.original_path):
                fail("the file to be processed isn't there")
                return False
            else:
                win("found the file")
            
            # md5
            self.md5 = md5file(self.original_path)
            self.save()
            
            # get basic info
            try:
                audio_info = audioprocessing.audio_info(self.original_path)
                win("got the audio info")
            except Exception, e:
                fail("audio information extraction has failed", e)
                return False
            
            self.samplerate = audio_info["samplerate"]
            self.bitrate = audio_info["bitrate"]
            self.bitdepth = audio_info["bits"]
            self.channels = audio_info["channels"]
            self.duration = audio_info["duration"]
            self.type = audio_info["type"]
            self.save()
            
            # convert to wave file
            tmp_wavefile = tempfile.mktemp(suffix=".wav", prefix=str(self.id))
            try:
                audioprocessing.convert_to_wav(self.original_path, tmp_wavefile)
                win("converted to wave file: " + tmp_wavefile)
            except Exception, e:
                fail("conversion to wave file has failed", e)
                return False
            
            # create preview
            try:
                mp3_path = os.path.join(settings.DATA_PATH, paths["preview_path"])
                os.makedirs(os.path.dirname(mp3_path))
                audioprocessing.convert_to_mp3(tmp_wavefile, mp3_path)
                win("created mp3: " + mp3_path)
            except Exception, e:
                cleanup([tmp_wavefile])
                fail("conversion to mp3 has failed", e)
                return False
            
            try:
                waveform_path_m = os.path.join(settings.DATA_PATH, paths["waveform_path_m"])
                spectral_path_m = os.path.join(settings.DATA_PATH, paths["spectral_path_m"])
                audioprocessing.create_wave_images(tmp_wavefile, waveform_path_m, spectral_path_m, 120, 71, 2048)
                win("created png, medium size: " + waveform_path_m)
            except Exception, e:
                cleanup([tmp_wavefile])
                fail("conversion to mp3 has failed", e)
                return False

            try:
                waveform_path_l = os.path.join(settings.DATA_PATH, paths["waveform_path_l"])
                spectral_path_l = os.path.join(settings.DATA_PATH, paths["spectral_path_l"])
                audioprocessing.create_wave_images(tmp_wavefile, waveform_path_l, spectral_path_l, 900, 201, 2048)
                win("created png, large size: " + waveform_path_l)
            except Exception, e:
                cleanup([tmp_wavefile])
                fail("conversion to mp3 has failed", e)
                return False

            cleanup([tmp_wavefile])
            self.processing_state = "OK"
            self.save()
            
            return True
            # create png SMALL
                
    @models.permalink
    def get_absolute_url(self):
        return ('sound', (smart_unicode(self.id),))
    
    class Meta(SocialModel.Meta):
        ordering = ("-created", )


class Pack(SocialModel):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)
    name_slug = models.SlugField(max_length=255, db_index=True)
    
    description = models.TextField()

    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __unicode__(self):
        return u"%s by %s" % (self.name, self.user)

    @models.permalink
    def get_absolute_url(self):
        return ('pack', (smart_unicode(self.id),))    
    
    class Meta(SocialModel.Meta):
        unique_together = ('user', 'name')
        ordering = ("-created",)


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