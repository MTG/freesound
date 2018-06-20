# -*- coding: utf-8 -*-

#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.utils.encoding import smart_unicode
import uuid
from utils.mail import send_mail_template

class Queue(models.Model):
    name            = models.CharField(max_length=128)
    groups          = models.ManyToManyField(Group)
    notify_by_email = models.BooleanField()

    def __unicode__(self):
        return self.name


def defaultkey():
    return str(uuid.uuid4()).replace('-','')


class Ticket(models.Model):
    title           = models.CharField(max_length=256)
    status          = models.CharField(max_length=128)
    key             = models.CharField(max_length=32, db_index=True, default=defaultkey)
    created         = models.DateTimeField(db_index=True, auto_now_add=True)
    modified        = models.DateTimeField(auto_now=True)
    comment_date    = models.DateTimeField(null=True)
    last_commenter  = models.ForeignKey(User, related_name='commented_tickets', null=True)
    sender          = models.ForeignKey(User, related_name='sent_tickets', null=True)
    sender_email    = models.EmailField(null=True)
    assignee        = models.ForeignKey(User, related_name='assigned_tickets', null=True)
    queue           = models.ForeignKey(Queue, related_name='tickets')
    sound           = models.OneToOneField('sounds.Sound', null=True, on_delete=models.SET_NULL)

    NOTIFICATION_QUESTION     = 'tickets/email_notification_question.txt'
    NOTIFICATION_APPROVED     = 'tickets/email_notification_approved.txt'
    NOTIFICATION_APPROVED_BUT = 'tickets/email_notification_approved_but.txt'
    NOTIFICATION_DELETED      = 'tickets/email_notification_deleted.txt'
    NOTIFICATION_UPDATED      = 'tickets/email_notification_updated.txt'
    NOTIFICATION_WHITELISTED  = 'tickets/email_notification_whitelisted.txt'

    MODERATOR_ONLY = 1
    USER_ONLY = 2
    USER_AND_MODERATOR = 3


    def get_n_last_non_moderator_only_comments(self, n):
        """
        Get the last n comments that are not 'moderator only' from the self ticket
        """
        ticket_comments = self.messages.all().filter(moderator_only=False).order_by('-created')
        return list(ticket_comments)[:n] # converting from Django QuerySet to python list in order to use negative indexing

    def send_notification_emails(self, notification_type, sender_moderator):
        ticket = self
        send_to = []
        # send message to assigned moderator
        if sender_moderator in [Ticket.MODERATOR_ONLY, Ticket.USER_AND_MODERATOR]:
            if self.assignee:
                user_to = self.assignee if self.assignee else False
                send_mail_template(u'A freesound moderator handled your upload.',
                                   notification_type,
                                   locals(),
                                   user_to=self.assignee)
        # send message to user
        if sender_moderator in [Ticket.USER_ONLY, Ticket.USER_AND_MODERATOR]:
            user_to = self.sender if self.sender else False
            email_to = user_to.email if user_to else ticket.sender_email
            if self.sender:
                send_mail_template(u'A freesound moderator handled your upload.',
                                   notification_type,
                                   locals(),
                                   user_to=user_to)

    def get_absolute_url(self):
        return reverse('ticket', args=[smart_unicode(self.key)])

    def __unicode__(self):
        return u"pk %s, key %s" % (self.id, self.key)

    class Meta:
        ordering = ("-created",)
        permissions = (
            ("can_change_status", "Can change the status of the ticket."),
            ("can_change_queue", "Can change the queue of the ticket."),
            ("can_moderate", "Can moderate stuff.")
        )


class TicketComment(models.Model):
    sender          = models.ForeignKey(User, null=True)
    text            = models.TextField()
    created         = models.DateTimeField(auto_now_add=True)
    ticket          = models.ForeignKey(Ticket, related_name='messages')
    moderator_only  = models.BooleanField(default=False)

    def __unicode__(self):
        return u"<# Message - ticket_id: %s, ticket_key: %s>" % \
                    (self.ticket.id, self.ticket.key)

    class Meta:
        ordering = ("-created",)
        permissions = (
            ("can_add_moderator_only_message", "Can add read-by-moderator-only messages."),
        )

def create_ticket_message(sender, instance, created, **kwargs):
    if created:
        instance.ticket.last_commenter = instance.sender
        instance.ticket.comment_date = instance.created
        instance.ticket.save()


post_save.connect(create_ticket_message, sender=TicketComment)


class UserAnnotation(models.Model):
    sender          = models.ForeignKey(User, related_name='sent_annotations')
    user            = models.ForeignKey(User, related_name='annotations')
    text            = models.TextField()
