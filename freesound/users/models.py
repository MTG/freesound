# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.ForeignKey(User)
    # add many many more things here :)
    
    whitelisted = models.BooleanField(default=False)
    newsletter = models.BooleanField(default=True)