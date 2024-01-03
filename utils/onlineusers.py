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

from datetime import timedelta, datetime
from django.core.cache import cache

ONLINE_MINUTES = 10
CACHE_KEY = 'online_user_ids'

_last_purged = datetime.now()


def get_online_users():
    user_dict = cache.get(CACHE_KEY)
    return hasattr(user_dict, 'keys') and user_dict.keys() or []


def cache_online_users(request):
    if request.user.is_anonymous:
        return
    user_dict = cache.get(CACHE_KEY)
    if not user_dict:
        user_dict = {}

    now = datetime.now()

    # Check if user has marked the option for not being shown in online users list
    if not request.user.profile.not_shown_in_online_users_list:
        user_dict[request.user.id] = now

    # purge
    global _last_purged
    if _last_purged + timedelta(minutes=ONLINE_MINUTES) < now:
        purge_older_than = now - timedelta(minutes=ONLINE_MINUTES)
        for user_id, last_seen in user_dict.copy().items():
            if last_seen < purge_older_than:
                del (user_dict[user_id])
        _last_purged = now

    cache.set(CACHE_KEY, user_dict, 60 * 60 * 24)
