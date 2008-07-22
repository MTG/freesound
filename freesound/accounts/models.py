# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
from general.models import SocialModel

class Profile(SocialModel):
    user = models.ForeignKey(User, unique=True)
    # add many many more things here :)
    
    home_page = models.URLField(null=True, blank=True, default=None)
    about = models.TextField(null=True, blank=True, default=None)
    newsletter = models.BooleanField(default=True, db_index=True)
    
    whitelisted = models.BooleanField(default=False, db_index=True)
    
    def __unicode__(self):
        return self.user.username
    
    @models.permalink
    def get_absolute_url(self):
        return ('account', (smart_unicode(self.user.username),))