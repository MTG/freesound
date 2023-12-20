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

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_str


class MessageBody(models.Model):
    body = models.TextField()

    def __str__(self):
        return self.body[0:30] + "[...]"


class Message(models.Model):
    """
    send message >> creates 2 mails in database:
        in sent messages bram:
            from bram
            to gerard
            sent = 1
            archived = 0
            read = 0 (although this doesn't matter for "sent" mails)

        in inbox gerard:
            from bram
            to gerard
            sent = 0 (received email by gerard)
            archived = 0
            read = 0

    note that the "is_sent" property means that this object is the sender's copy of the message.
    we could consider renaming this property to "is_sender_copy"


    gerard opens message:
        in inbox gerard:
            from bram
            to gerard
            sent = 0
            archived = 0
            read = 1

    gerard archives message:
        in inbox gerard:
            from bram
            to gerard
            sent = 0
            archived = 1
            read = 1

    inbox gerard contains:
        where
            to=gerard and
            sent=0
            archived=0

    sent-messages bram contains:
        where
            from=bram
            sent=1
            archived=0

    etc...
    """

    user_from = models.ForeignKey(User, related_name='messages_sent', on_delete=models.CASCADE)
    user_to = models.ForeignKey(User, related_name='messages_received', on_delete=models.CASCADE)

    subject = models.CharField(max_length=128)

    body = models.ForeignKey(MessageBody, on_delete=models.CASCADE)

    is_sent = models.BooleanField(default=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def get_absolute_url(self):
        return "message", (smart_str(self.id),)

    def __str__(self):
        return f"from: [{self.user_from}] to: [{self.user_to}]"

    class Meta:
        ordering = ('-created',)
