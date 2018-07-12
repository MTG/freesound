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
import urllib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.urls import reverse

from sounds.models import Sound
from utils.onlineusers import cache_online_users


def dont_redirect(path):
    return 'bulklicensechange' not in path \
        and 'logout' not in path \
        and 'tosacceptance' not in path \
        and 'tos_api' not in path \
        and 'tos_web' not in path \
        and 'privacy' not in path \
        and 'cookies' not in path \
        and 'contact' not in path \
        and not path.startswith(settings.MEDIA_URL)


class OnlineUsersHandler(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cache_online_users(request)
        response = self.get_response(request)
        return response


class BulkChangeLicenseHandler(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # check for authentication,
        # avoid infinite loop
        # allow user to logout (maybe a bit too much...)
        # don't run it for media URLs
        # N.B. probably better just to check for login in the URL
        if request.user.is_authenticated \
                and dont_redirect(request.get_full_path()):

            user = request.user
            cache_key = "has-old-license-%s" % user.id
            cache_info = cache.get(cache_key)

            if cache_info is None or 0 or not isinstance(cache_info, (list, tuple)):
                has_old_license = user.profile.has_old_license
                has_sounds = Sound.objects.filter(user=user).exists()
                cache.set(cache_key, [has_old_license, has_sounds], 2592000)  # 30 days cache
                if has_old_license and has_sounds:
                    return HttpResponseRedirect(reverse("bulk-license-change"))
            else:
                has_old_license = cache_info[0]
                has_sounds = cache_info[1]
                if has_old_license and has_sounds:
                    return HttpResponseRedirect(reverse("bulk-license-change"))
        response = self.get_response(request)
        return response


class FrontendPreferenceHandler(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        This middleware sets a session variable when the parameter 'new_frontend' is received.
        The 'render' method will use this session variable to display the new/old frontend
        """
        if request.GET.get(settings.FRONTEND_CHOOSER_REQ_PARAM_NAME, None):
            request.session[settings.FRONTEND_SESSION_PARAM_NAME] = \
                request.GET.get(settings.FRONTEND_CHOOSER_REQ_PARAM_NAME)
        response = self.get_response(request)
        return response


class TosAcceptanceHandler(object):
    """Checks if the user has accepted the updates to the Terms
    of Service due to the GDPR (May 2018).
    This replaces the agreement to the original ToS (2013, 2fd543f3a)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated \
                and dont_redirect(request.get_full_path()):

            user = request.user
            cache_key = 'has-accepted-tos2018-%s' % user.id
            cache_info = cache.get(cache_key)

            if not cache_info:
                has_accepted_tos = hasattr(user, 'gdpracceptance')
                if not has_accepted_tos:
                    url = '%s?%s' % (reverse('tos-acceptance'), urllib.urlencode({'next': request.get_full_path()}))
                    return HttpResponseRedirect(url)
                else:
                    cache.set(cache_key, 'yes', 2592000)  # 30 days cache
            else:
                # If there is cache it means the terms has been accepted
                pass

        response = self.get_response(request)
        return response
