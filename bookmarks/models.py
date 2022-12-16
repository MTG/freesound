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
from django.db import models

from sounds.models import Sound


class BookmarkCategory(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128, default="")
    
    def __unicode__(self):
        return u"%s" % self.name


class Bookmark(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=128, default="", blank=True)
    category = models.ForeignKey(BookmarkCategory, blank=True, null=True, default=None, related_name='bookmarks')
    sound = models.ForeignKey(Sound)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __unicode__(self):
        return u"Bookmark: %s" % self.name

    @property
    def category_name_or_uncategorized(self):
        if self.category is None:
            return 'Uncategorized'
        else:
            return self.category.name

    @property
    def name_or_sound_name(self):
        # NOTE: this is no longer used in BW as we don't use the concept of custom names for boomarks
        if self.name:
            return self.name
        else:
            return self.sound.original_filename

    class Meta(object):
        ordering = ("-created", )
