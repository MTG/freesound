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
from django.db import models
from django.urls import reverse
from django.utils.encoding import smart_unicode


class GeoTag(models.Model):
    user = models.ForeignKey(User)

    lat = models.FloatField(db_index=True)
    lon = models.FloatField(db_index=True)
    zoom = models.IntegerField()

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __unicode__(self):
        return u"%s (%f,%f)" % (self.user, self.lat, self.lon)

    def get_absolute_url(self):
        return reverse('geotag', args=[smart_unicode(self.id)])
