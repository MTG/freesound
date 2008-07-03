# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models

class Image(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=512)
    
    # base of the filename, this will be something like:
    # fileid__username__filenameslug
    base_filename_slug = models.CharField(max_length=512)
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = generic.GenericForeignKey()
        
    # moderation
    MODERATION_STATE_CHOICES = (
                                ("PE",_('Pending')),
                                ("OK",_('OK')),
                               )
    
    moderation_state = models.CharField(db_index=True, max_length=3, choices=MODERATION_STATE_CHOICES)
    moderation_date = models.DateTimeField(null=True, blank=True)
    
    created = models.DateTimeField()
    modified = models.DateTimeField()

    def __unicode__(self):
        return u"%s from %s" % (self.title, self.user)


class ImageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'title', 'base_filename_slug', 'content_object', 'created')
admin.site.register(Image, ImageAdmin)