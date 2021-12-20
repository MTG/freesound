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
import json
import math

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.encoding import smart_unicode

import pycountry
import reverse_geocoder


def coordinates_distance_to_km(lat1, lon1, lat2, lon2):
    # Inspired from https://stackoverflow.com/a/19412565
    R = 6373.0  # approximate radius of earth in km
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance


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

    def get_location_name(self):
        if settings.USE_TEXTUAL_LOCATION_NAMES_IN_BW:
            result = reverse_geocoder.search((self.lat, self.lon))[0]
            distance_in_km = coordinates_distance_to_km(float(result['lat']), float(result['lon']), self.lat, self.lon)
            if distance_in_km < 50:
                name_label = result['name'] + ', ' + result['admin1']
            else:
                name_label = result['admin1']
            country_name = pycountry.countries.get(alpha_2=result['cc']).name
            return '{}, {}'.format(name_label, country_name)
        else:
            return '{:.3f}, {:.3f}'.format(self.lat, self.lon)
