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
from django.contrib.auth.models import User
from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import smart_text
from django.urls import reverse

class Tag(models.Model):
    name = models.SlugField(unique=True, db_index=True, max_length=100)

    def __str__(self):
        return self.name

    def get_browse_tag_url(self):
        return reverse('tags', self.name)

    class Meta(object):
        ordering = ("name",)


class TaggedItem(models.Model):
    user = models.ForeignKey(User)

    tag = models.ForeignKey(Tag)

    #content_type = models.ForeignKey(ContentType, related_name='tags')
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = fields.GenericForeignKey()

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return u"%s tagged %s - %s: %s" % (self.user, self.content_type, self.content_type, self.tag)

    def get_absolute_url(self):
        return reverse('tag', args=[smart_text(self.tag.id)])

    class Meta(object):
        ordering = ("-created",)
        unique_together = (('tag', 'content_type', 'object_id'),)

# Class to get old tags ids linked to new tag ids
# The goal is to at some point deprecate the old tag ids completely
class FS1Tag(models.Model):
    # The old id from FS1
    fs1_id = models.IntegerField(unique=True, db_index=True)

    tag = models.ForeignKey(Tag)
