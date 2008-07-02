# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models

class Message(models.Model):
    user_from = models.ForeignKey(User, related_name='messages_sent')
    user_to = models.ForeignKey(User, related_name='messages_received')
    
    message = models.TextField()
    subject = models.CharField(max_length=128)
    
    read = models.BooleanField(default=False, db_index=True)
    deleted = models.BooleanField(default=False, db_index=True)
    
    created = models.DateTimeField(db_index=True)

    def __unicode__(self):
        return u"from: [%s] to: [%s]" % (self.user_from, self.user_to)


class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user_from', 'user_to')
    list_display = ('user_from', 'user_to', 'subject', 'read', 'deleted', 'created')

admin.site.register(Message, MessageAdmin)