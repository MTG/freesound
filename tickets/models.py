# -*- coding: utf-8 -*-
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import smart_unicode
import uuid


class Queue(models.Model):
    name            = models.CharField(max_length=128)
    groups          = models.ManyToManyField(Group)
    notify_by_email = models.BooleanField()
    
    def __unicode__(self):
        return self.name
    

class LinkedContent(models.Model):
    content_type    = models.ForeignKey(ContentType)
    object_id       = models.PositiveIntegerField(db_index=True)
    content_object  = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return u"<# LinkedContent - pk: %s, type: %s>" % (self.object_id, self.content_type)


class Ticket(models.Model):
    title           = models.CharField(max_length=256)
    source          = models.CharField(max_length=128)
    status          = models.CharField(max_length=128)
    key             = models.CharField(max_length=32, db_index=True, default=lambda: str(uuid.uuid4()).replace('-', ''))
    created         = models.DateTimeField(db_index=True, auto_now_add=True)
    modified        = models.DateTimeField(auto_now=True)
    sender          = models.ForeignKey(User, related_name='sent_tickets', null=True)
    sender_email    = models.EmailField(null=True)
    assignee        = models.ForeignKey(User, related_name='assigned_tickets', null=True)
    queue           = models.ForeignKey(Queue, related_name='tickets')
    content         = models.ForeignKey(LinkedContent, null=True)

    @models.permalink
    def get_absolute_url(self):
        return ('ticket', (smart_unicode(self.key),))
    
    def __unicode__(self):
        return u"<# Ticket - pk: %s, key: %s>" % (self.id, self.key)

    class Meta:
        ordering = ("-created",)
        

class TicketComment(models.Model):
    sender          = models.ForeignKey(User, null=True)
    text            = models.TextField()
    created         = models.DateTimeField(auto_now_add=True)
    ticket          = models.ForeignKey(Ticket, related_name='messages')
    moderator_only  = models.BooleanField()

    def __unicode__(self):
        return u"<# Message - ticket_id: %s, ticket_key: %s>" % \
                    (self.ticket.id, self.ticket.key)

    class Meta:
        ordering = ("-created",)
        

class UserAnnotation(models.Model):
    sender          = models.ForeignKey(User, related_name='sent_annotations')
    user            = models.ForeignKey(User, related_name='annotations')
    text            = models.TextField()
    