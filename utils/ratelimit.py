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

import random

from django.conf import settings

from utils.logging_filters import get_client_ip

def get_ip_or_random_ip(request):
    ip = get_client_ip(request)
    if ip == '-':
        # If for some reason an ip is not returned by get_client_ip, we generate a random number to avoid putting all
        # requests in the same key
        ip = str(random.random())
    return ip

def key_for_ratelimiting(group, request):
    return '{}-{}'.format(group, get_ip_or_random_ip(request))

def rate_per_ip(group, request):
    ip = get_ip_or_random_ip(request)
    if ip in settings.BLOCKED_IPS:
        return '0/s'
    return settings.RATELIMITS(group, settings.RATELIMIT_DEFAULT_GROUP_RATELIMIT)
