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

from builtins import object
import sounds
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete


class Comment(models.Model):
    user = models.ForeignKey(User)
    sound = models.ForeignKey('sounds.Sound', null=True, related_name='comments')
    comment = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', default=None)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s comment on %s" % (self.user, self.sound)

    class Meta(object):
        ordering = ('-created', )


def on_delete_comment(sender, instance, **kwargs):
    try:
        instance.sound.post_delete_comment()
    except sounds.models.Sound.DoesNotExist:
        """
        If this comment is deleted as a result of its parent sound being deleted, the
        sound will no longer exist so we don't need to update it
        """
        pass
post_delete.connect(on_delete_comment, sender=Comment)
