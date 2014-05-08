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

from rest_framework.throttling import SimpleRateThrottle
from exceptions import Throttled
from settings import APIV2_BASIC_THROTTLING_RATES_PER_LEVELS


class ClientBasedThrottling(SimpleRateThrottle):
    """
    This throttling class applies different throttling rates depending on the access level of the API client.
    For session request we apply a common throttling rate as there is no API client associated.
    """
    cache_format = 'throtte_%(identity)s'
    client = None

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # Get the ApiV2Client that made the request
        auth_method_name = request.successful_authenticator.authentication_method_name
        if auth_method_name == "OAuth2":
            self.client = request.auth.client.apiv2_client
        elif auth_method_name == "Token":
            self.client = request.auth
        elif auth_method_name == "Session":
            self.client = None

        # Determine the rates of the client depending on its level
        client_throttle_level = 1  # TODO: get level from client table
        try:
            limit_rates = view.throttling_rates_per_level[client_throttle_level]
        except:
            limit_rates = APIV2_BASIC_THROTTLING_RATES_PER_LEVELS[client_throttle_level]

        # Apply all the limit rates for the corresponding level
        if limit_rates:
            for rate in limit_rates:
                self.rate = rate
                self.num_requests, self.duration = self.parse_rate(rate)
                passes_throttle = super(ClientBasedThrottling, self).allow_request(request, view)
                if not passes_throttle:
                    msg = "Request was throttled because of exceeding a request limit rate (%s)" % rate
                    if client_throttle_level == 0:
                        # Prevent returning a absurd message like "exceeding a request limit rate (0/minute)"
                        msg = "Request was throttled because the ApiV2 credential has been suspended"
                    raise Throttled(msg=msg)
        return True

    def get_cache_key(self, request, view):
        if self.client:
            return self.cache_format % {
                'identity': self.client.client_id
            }
        else:
            # If using session based auth, we use the user id as identity for throttling cache
            return self.cache_format % {
                'identity': request.user.id
            }