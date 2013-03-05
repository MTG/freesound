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
import uuid

def generate_key():
    return str(uuid.uuid4()).replace('-','')

class ApiKey(models.Model):
    STATUS_CHOICES = (('OK',  'Approved'),
                      ('REJ', 'Rejected'),
                      ('REV', 'Revoked'),
                      ('PEN', 'Pending'))
    
    DEFAULT_STATUS = 'OK'

    key            = models.CharField(max_length=32, default=generate_key, db_index=True, unique=True)
    user           = models.ForeignKey(User, related_name='api_keys')
    status         = models.CharField(max_length=3, default=DEFAULT_STATUS, choices=STATUS_CHOICES)
    name           = models.CharField(max_length=64)
    url            = models.URLField()
    description    = models.TextField(blank=True)
    accepted_tos   = models.BooleanField(default=False)
