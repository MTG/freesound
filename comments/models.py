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

from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_delete


class Comment(models.Model):
    user = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    comment = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', default=None)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __unicode__(self):
        return u"%s comment on %s - %s" % (self.user, self.content_type, self.content_type)
    
    class Meta:
        ordering = ('-created', )


def on_delete_comment(sender, instance, **kwargs):
    if instance.content_object.__class__.__name__ == 'Sound':
        instance.content_object.post_delete_comment()
post_delete.connect(on_delete_comment, sender=Comment)
