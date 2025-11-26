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

import ipaddress
import logging
import random
import time

from django.conf import settings
from django.core.cache import cache

from utils.logging_filters import get_client_ip

console_logger = logging.getLogger("console")

last_cached_blocked_ips = []
last_cached_blocked_ips_timestamp = 0


def get_ips_to_block():
    """
    Get a list of IPs to block. Returned IPs include a combination of the IPs listed in settings.BLOCKED_IPS and
    a list of IPs cached with the key settings.CACHED_BLOCKED_IPS_KEY. To avoid many queries to the cache, this
    function stores the cached IPs in a global variable and only refreshes them after settings.CACHED_BLOCKED_IPS_TIME
    seconds have passed since the last time the cache was queried for settings.CACHED_BLOCKED_IPS_KEY. This effectively
    adds a 2nd layer of cache.

    Returns:
        List[str]: List of IPs to block
    """
    global last_cached_blocked_ips, last_cached_blocked_ips_timestamp
    now = time.time()
    if now - last_cached_blocked_ips_timestamp > settings.CACHED_BLOCKED_IPS_TIME:
        last_cached_blocked_ips = cache.get(settings.CACHED_BLOCKED_IPS_KEY, None)
        last_cached_blocked_ips_timestamp = now
    if last_cached_blocked_ips is not None:
        return list(set(settings.BLOCKED_IPS + last_cached_blocked_ips))
    else:
        return settings.BLOCKED_IPS


def add_new_ip_to_block(ip):
    """
    Add a new IP to the cached list of IPs to block so that further requests to that IP will get blocked.
    Note that it might take up to settings.CACHED_BLOCKED_IPS_TIME before that IP actually starts to
    get blocked.

    This method is intended to be used from the console as a quick way of blocking an IP. However, note that
    if the cache gets cleared, that IP will no longer be blocked. For long-time persistent IP blocking,
    settings.BLOCKED_IPS should be used. To use this method, login in a Django console and type:

        from utils.ratelimit import add_new_ip_to_block
        add_new_ip_to_block("1.2.3.4")

    Args:
        ip (str): IP to block. Can also specify a range as described in ipaddress.IPv4Network docs.
    """
    try:
        ipaddress.ip_network(str(ip))
    except ValueError as e:
        console_logger.info(f"The provided IP {ip} is not valid: {e}")
        return

    cached_ips_to_block = cache.get(settings.CACHED_BLOCKED_IPS_KEY, None)
    if cached_ips_to_block is not None:
        cached_ips_to_block += [ip]
    else:
        cached_ips_to_block = [ip]
    cache.set(settings.CACHED_BLOCKED_IPS_KEY, cached_ips_to_block)


def ip_is_blocked(ip):
    """
    Determines whether an IP should be blocked. To do that, it uses ipaddress.ip_network objects which support
    IP comparison using ranges.

    Args:
        ip (str): IP to check. Can also specify a range as described in ipaddress.IPv4Network docs.

    Returns:
        bool: True if the IP should be blocked, False otherwise.

    """
    for ip_to_block in get_ips_to_block():
        if ipaddress.ip_network(str(ip_to_block)).overlaps(ipaddress.ip_network(str(ip))):
            return True
    return False


def get_ip_or_random_ip(request):
    ip = get_client_ip(request)
    if ip == "-":
        # If for some reason an ip is not returned by get_client_ip, we generate a random number to avoid putting all
        # requests in the same key
        ip = str(random.random())
    return ip


def key_for_ratelimiting(group, request):
    return f"{group}-{get_ip_or_random_ip(request)}"


def rate_per_ip(group, request):
    ip = get_ip_or_random_ip(request)
    if ip_is_blocked(ip):
        return "0/s"
    return settings.RATELIMITS.get(group, settings.RATELIMIT_DEFAULT_GROUP_RATELIMIT)
