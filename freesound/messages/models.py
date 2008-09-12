# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models

class Message(models.Model):
    user_from = models.ForeignKey(User, related_name='messages_sent')
    user_to = models.ForeignKey(User, related_name='messages_received')
    
    message = models.TextField()
    subject = models.CharField(max_length=128)
    
    parent = models.ForeignKey('self', blank=True, null=True, default=None, related_name='replies')
        
    read = models.BooleanField(default=False, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)
    
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"from: [%s] to: [%s]" % (self.user_from, self.user_to)
    
    class Meta:
        ordering = ('-created',)