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
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.encoding import smart_str
from mapbox import Geocoder

web_logger = logging.getLogger("web")


class GeoTag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lat = models.FloatField(db_index=True)
    lon = models.FloatField(db_index=True)
    zoom = models.IntegerField()
    information = models.JSONField(null=True)
    location_name = models.CharField(max_length=255, default="")
    should_update_information = models.BooleanField(null=False, default=True)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.lat:f},{self.lon:f})"

    def get_absolute_url(self):
        return reverse('geotag', args=[smart_str(self.id)])

    def retrieve_location_information(self):
        """Use the mapbox API to retrieve information about the latitude and longitude of this geotag.
        If no iformation has been retrieved from mapbox and a mapbox access token is available, retrieve and
        store that information. Then, pre-process that information to save a place name for display purposes.
        """
        if settings.MAPBOX_ACCESS_TOKEN and (self.information is None or self.should_update_information):
            perm_geocoder = Geocoder(name='mapbox.places-permanent', access_token=settings.MAPBOX_ACCESS_TOKEN)
            try:
                response = perm_geocoder.reverse(lon=self.lon, lat=self.lat)
                self.information = response.json()
                self.should_update_information = False
                self.save()
            except Exception as e:
                pass
                
        if self.information is not None:
            features = self.information.get('features', [])
            if features:
                try:
                    # Try with "place" feature
                    self.location_name = [feature for feature in features if 'place' in feature['place_type']][0]['place_name']
                except IndexError:
                    # If "place" feature is not avialable, use "locality" feature
                    try:
                        self.location_name = [feature for feature in features if 'locality' in feature['place_type']][0]['place_name']
                    except IndexError:
                        # If "place" nor "locality" features are avialable, use "region"
                        try:
                            self.location_name = [feature for feature in features if 'region' in feature['place_type']][0]['place_name']
                        except:
                            # It is not possible to derive a name...
                            pass
                self.save()
