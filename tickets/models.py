# -*- coding: utf-8 -*-
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import smart_unicode
import uuid, logging
from utils.mail import send_mail_template

logger = logging.getLogger("web")

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

    NOTIFICATION_QUESTION     = 'tickets/email_notification_question.txt'
    NOTIFICATION_APPROVED     = 'tickets/email_notification_approved.txt'
    NOTIFICATION_APPROVED_BUT = 'tickets/email_notification_approved_but.txt'
    NOTIFICATION_DELETED      = 'tickets/email_notification_deleted.txt'
    NOTIFICATION_UPDATED      = 'tickets/email_notification_updated.txt'

    def send_notification_emails(self, notification_type):
        ticket = self
        # last message from uploader (we assume self.sender is the uploader)
        messages = TicketComment.objects.filter(ticket=ticket).order_by('-id')
        last_message = messages[0] if messages else False
        if last_message and (last_message.sender == None or last_message.sender == self.sender):
            #send message to assigned moderator
                # There is probably always a moderator assigned, but ok.. let's just check
            email_addr = self.assignee.email if self.assignee else False
            user_to = self.assignee if self.assignee else False
        # last message by someone who didn't start the ticket
        else:
            # send message to user
            email_addr = self.sender.email if self.sender else self.sender_email
            user_to = self.sender if self.sender else False
        if not email_addr:
            logger.error('E-mail address to send notifications could not be determined. What gives?')
            return
        send_mail_template(u'A freesound moderator handled your upload.', 
                           notification_type, 
                           locals(), 
                           'no-reply@freesound.org', 
                           email_addr)
        

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
    