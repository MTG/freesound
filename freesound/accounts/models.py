# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import SocialModel
from geotags.models import GeoTag

class Profile(SocialModel):
    user = models.OneToOneField(User)
    
    about = models.TextField(null=True, blank=True, default=None)
    home_page = models.URLField(null=True, blank=True, default=None)
    signature = models.TextField(max_length=256, null=True, blank=True)
    geotag = models.ForeignKey(Geotag, null=True, blank=True, default=None)

    wants_newsletter = models.BooleanField(default=True, db_index=True)
    is_whitelisted = models.BooleanField(default=False, db_index=True)
    
    last_action_time = models.DateTimeField()
    
    num_sounds = models.PositiveIntegerField(editable=False, default=0)
    num_posts = models.PositiveIntegerField(editable=False, default=0)
    
    def __unicode__(self):
        return self.user.username
    
    @models.permalink
    def get_absolute_url(self):
        return ('account', (smart_unicode(self.user.username),))
    
    class Meta(SocialModel.Meta):
        ordering = ('-user__date_joined', )