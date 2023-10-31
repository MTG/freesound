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

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key


def get_template_cache_key(fragment_name, *variables):
    return make_template_fragment_key(fragment_name, variables)


def invalidate_template_cache(fragment_name, *variables):
    cache_key = get_template_cache_key(fragment_name, *variables)
    cache.delete(cache_key)


def invalidate_user_template_caches(user_id):
    invalidate_template_cache('user_header', user_id)
    invalidate_template_cache('bw_user_header', user_id)
    invalidate_template_cache('bw_user_profile_tags', user_id)
    invalidate_template_cache('bw_user_profile_followers_count', user_id)
    invalidate_template_cache('bw_user_profile_following_count', user_id)
    invalidate_template_cache('bw_user_profile_following_tags_count', user_id)
    invalidate_template_cache('bw_user_profile_latest_packs_section', user_id, True)
    invalidate_template_cache('bw_user_profile_latest_packs_section', user_id, False)
    cache.delete(settings.USER_STATS_CACHE_KEY.format(user_id))


def invalidate_all_moderators_header_cache():
    mods = Group.objects.get(name='moderators').user_set.all()
    for mod in mods:
        invalidate_user_template_caches(mod.id)

