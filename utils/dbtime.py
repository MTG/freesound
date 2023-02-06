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

from datetime import datetime

from django.conf import settings
from django.core.cache import cache

from sounds.models import Sound, Download


class DBTime:
    last_time = None

    @staticmethod
    def get_last_time():
        if not settings.DEBUG:
            return datetime.now()
        if DBTime.last_time is None:
            cache_key = "last_download_time"
            last_time = cache.get(cache_key)
            if not last_time:
                try:
                    last_time = Sound.objects.order_by('-created')[0].created
                except Download.DoesNotExist:
                    last_time = datetime.now()
            cache.set(cache_key, DBTime.last_time, 60 * 60 * 24)
            DBTime.last_time = last_time
        return DBTime.last_time
