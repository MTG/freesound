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
from django.core.cache import caches
from rest_framework.throttling import SimpleRateThrottle

from apiv2.exceptions import Throttled

cache_api_monitoring = caches["api_monitoring"]


class FreesoundSimpleRateThrottle(SimpleRateThrottle):
    cache = cache_api_monitoring
    client = None
    limit_list_index = 0

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # Get the ApiV2Client that made the request and its throttling level
        self.client, client_throttle_level = self.get_client_and_throttling_level_from_request(request)

        # Get the limit rate for the client's throttling level from the view or settings
        rate = self.get_limit_rate_from_throttling_level(view, client_throttle_level)

        # Check if request should be allowed. Note hat no rate means unlimited usage
        if rate:
            self.rate = rate
            self.num_requests, self.duration = self.parse_rate(rate)
            passes_throttle = super().allow_request(request, view)
            if not passes_throttle:
                msg = f"Request was throttled because of exceeding a request limit rate ({rate})"
                if client_throttle_level == 0:
                    # Prevent returning a absurd message like "exceeding a request limit rate (0/minute)"
                    msg = "Request was throttled because the ApiV2 credential has been suspended"
                raise Throttled(msg=msg, request=request)
        return True

    @classmethod
    def get_limit_rate_from_throttling_level(cls, view, throttling_level):
        try:
            limit_rates = view.throttling_rates_per_level[throttling_level]
        except:
            # Fallback to basic throttling levels if the view has not defined the throttling rates per level
            limit_rates = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS[throttling_level]
        return limit_rates[cls.limit_list_index]

    @classmethod
    def get_client_and_throttling_level_from_request(cls, request):
        auth_method_name = request.successful_authenticator.authentication_method_name
        if auth_method_name == "OAuth2":
            client = request.auth.application.apiv2_client
            client_throttle_level = int(client.throttling_level)
        elif auth_method_name == "Token":
            client = request.auth
            client_throttle_level = int(client.throttling_level)
        elif auth_method_name == "Session":
            client = None
            client_throttle_level = 1
        return client, client_throttle_level

    @classmethod
    def get_cache_key_for_request_and_client(cls, request, client=None):
        if client is None:
            client, _ = cls.get_client_and_throttling_level_from_request(request)
        if client:
            # Apply the retriction per user and not per client (so that a single user cannot bypass limits by using multiple clients)
            return cls.cache_format % {"identity": client.user_id}
        else:
            return cls.cache_format % {"identity": request.user.id}

    def get_cache_key(self, request, view):
        return self.get_cache_key_for_request_and_client(request, client=self.client)


class ClientBasedThrottlingBurst(FreesoundSimpleRateThrottle):
    """
    This throttling class applies different throttling rates depending on the access level of the API client.
    Each access level is defined with a burst limit and a sustained limit. This class checks the burst limit.
    For session request we apply a common throttling rate as there is no API client associated.
    """

    cache_format = "throttle_burst_%(identity)s"
    limit_list_index = 0


class ClientBasedThrottlingSustained(FreesoundSimpleRateThrottle):
    """
    This throttling class applies different throttling rates depending on the access level of the API client.
    Each access level is defined with a burst limit and a sustained limit. This class checks the sustained limit.
    For session request we apply a common throttling rate as there is no API client associated.
    """

    cache_format = "throttle_sustained_%(identity)s"
    limit_list_index = 1


class IpBasedThrottling(FreesoundSimpleRateThrottle):
    """
    This throttling class applies different ip-based throttling rates depending on the access level of the API client.
    Depending on the client level, a maximum number of connections from different ips are allowed for a given time period.
    For session request we apply a common throttling rate as there is no API client associated.
    """

    cache_format = "throttle_ip_%(identity)s"
    limit_list_index = 2
    cache = cache_api_monitoring
    client = None
    ip = None
    ip_in_history = None

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # Get the ApiV2Client that made the request and its throttling level
        self.client, client_throttle_level = self.get_client_and_throttling_level_from_request(request)

        # Get request ip
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            self.ip = x_forwarded_for.split(",")[0].strip()
        else:
            self.ip = "-"

        # Get the limit rate for the client's throttling level from the view or settings
        rate = self.get_limit_rate_from_throttling_level(view, client_throttle_level)
        if rate:
            self.rate = rate
            self.num_requests, self.duration = self.parse_rate(rate)

            if self.rate is None:
                return True

            self.key = self.get_cache_key(request, view)
            if self.key is None:
                return True

            self.history = self.cache.get(self.key, [])
            self.now = self.timer()

            # Drop any requests from the history which have now passed the
            # throttle duration
            while self.history and self.history[-1][0] <= self.now - self.duration:
                self.history.pop()
            self.ip_in_history = self.ip in [history_ip for history_now, history_ip in self.history]

            if self.ip_in_history:
                return True
            else:
                if len(self.history) >= self.num_requests:
                    passes_throttle = self.throttle_failure()
                else:
                    passes_throttle = self.throttle_success()

            if not passes_throttle:
                msg = f"Request was throttled because of exceeding the concurrent ip limit rate ({rate})"
                if client_throttle_level == 0:
                    # Prevent returning a absurd message like "exceeding a request limit rate (0/minute)"
                    msg = "Request was throttled because the ApiV2 credential has been suspended"
                raise Throttled(msg=msg, request=request)
        return True

    def throttle_success(self):
        """
        Inserts the current request's timestamp and request along with the key
        into the cache if the ip is not already in the list.
        """
        self.history.insert(0, [self.now, self.ip])
        self.cache.set(self.key, self.history, self.duration)
        return True
