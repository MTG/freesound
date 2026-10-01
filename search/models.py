#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
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


class SearchQuery(models.Model):
    class SearchQueryType(models.TextChoices):
        SEARCH_PAGE = "sp"
        TAGS_PAGE = "tp"
        API = "api"

    query = models.CharField(max_length=255)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    QUERY_TYPES = SearchQueryType.choices
    query_type = models.CharField(max_length=3, choices=SearchQueryType.choices)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    url = models.CharField(max_length=2048)
    num_results = models.IntegerField()
    query_time = models.FloatField()
    ip = models.CharField(max_length=45)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"SearchQuery(query={self.query}, type={self.query_type}, user={self.user}, created={self.created})"
