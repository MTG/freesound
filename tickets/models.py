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

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_save
from django.utils.encoding import smart_str
import uuid
from utils.mail import send_mail_template


def defaultkey():
    return str(uuid.uuid4()).replace('-','')


class Ticket(models.Model):
    title           = models.CharField(max_length=256)
    status          = models.CharField(max_length=128)
    key             = models.CharField(max_length=32, db_index=True, default=defaultkey)
    created         = models.DateTimeField(db_index=True, auto_now_add=True)
    modified        = models.DateTimeField(auto_now=True)
    comment_date    = models.DateTimeField(null=True)
    last_commenter  = models.ForeignKey(User, related_name='commented_tickets', null=True, on_delete=models.SET_NULL)
    sender          = models.ForeignKey(User, related_name='sent_tickets', null=True, on_delete=models.SET_NULL)
    sender_email    = models.EmailField(null=True)
    assignee        = models.ForeignKey(User, related_name='assigned_tickets', null=True, on_delete=models.SET_NULL)
    sound           = models.OneToOneField('sounds.Sound', null=True, on_delete=models.SET_NULL)

    NOTIFICATION_QUESTION     = 'emails/email_notification_question.txt'
    NOTIFICATION_APPROVED     = 'emails/email_notification_approved.txt'
    NOTIFICATION_APPROVED_BUT = 'emails/email_notification_approved_but.txt'
    NOTIFICATION_DELETED      = 'emails/email_notification_deleted.txt'
    NOTIFICATION_UPDATED      = 'emails/email_notification_updated.txt'
    NOTIFICATION_WHITELISTED  = 'emails/email_notification_whitelisted.txt'

    MODERATOR_ONLY = 1
    USER_ONLY = 2

    def get_n_last_non_moderator_only_comments(self, n):
        """
        Get the last n comments that are not 'moderator only' from the self ticket
        """
        ticket_comments = self.messages.all().filter(moderator_only=False).order_by('-created')
        return list(ticket_comments)[:n] # converting from Django QuerySet to python list in order to use negative indexing

    def send_notification_emails(self, notification_type, sender_moderator):
        # send message to assigned moderator
        if sender_moderator in [Ticket.MODERATOR_ONLY]:
            if self.assignee:
                tvars = {'ticket': self,
                         'user_to': self.assignee}
                send_mail_template(settings.EMAIL_SUBJECT_MODERATION_HANDLED,
                                   notification_type,
                                   tvars,
                                   user_to=self.assignee)
        # send message to user
        if sender_moderator in [Ticket.USER_ONLY]:
            if self.sender:
                tvars = {'ticket': self,
                         'user_to': self.sender}
                send_mail_template(settings.EMAIL_SUBJECT_MODERATION_HANDLED,
                                   notification_type,
                                   tvars,
                                   user_to=self.sender)

    def get_absolute_url(self):
        return reverse('ticket', args=[smart_str(self.key)])

    def __str__(self):
        return f"pk {self.id}, key {self.key}"

    class Meta:
        ordering = ("-created",)
        permissions = (
            ("can_moderate", "Can moderate stuff."),
        )


class TicketComment(models.Model):
    sender          = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    text            = models.TextField()
    created         = models.DateTimeField(auto_now_add=True)
    ticket          = models.ForeignKey(Ticket, related_name='messages', on_delete=models.CASCADE)
    moderator_only  = models.BooleanField(default=False)

    def __str__(self):
        return "<# Message - ticket_id: %s, ticket_key: %s>" % \
                    (self.ticket.id, self.ticket.key)

    class Meta:
        ordering = ("-created",)


def create_ticket_message(sender, instance, created, **kwargs):
    if created:
        instance.ticket.last_commenter = instance.sender
        instance.ticket.comment_date = instance.created
        instance.ticket.save()


post_save.connect(create_ticket_message, sender=TicketComment)


class UserAnnotation(models.Model):
    sender = models.ForeignKey(User, related_name='sent_annotations', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='annotations', on_delete=models.CASCADE)
    text = models.TextField()
