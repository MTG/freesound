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
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.urls import reverse

from sounds.models import Sound
from utils.onlineusers import cache_online_users


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
                and 'bulklicensechange' not in request.get_full_path() \
                and 'logout' not in request.get_full_path() \
                and 'tosacceptance' not in request.get_full_path() \
                and not request.get_full_path().startswith(settings.MEDIA_URL):

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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated \
                and 'tosacceptance' not in request.get_full_path() \
                and 'logout' not in request.get_full_path() \
                and 'tos_api' not in request.get_full_path() \
                and 'tos_web' not in request.get_full_path() \
                and 'contact' not in request.get_full_path() \
                and 'bulklicensechange' not in request.get_full_path() \
                and not request.get_full_path().startswith(settings.MEDIA_URL):

            user = request.user
            cache_key = "has-accepted-tos-%s" % user.id
            cache_info = cache.get(cache_key)

            if not cache_info:
                has_accepted_tos = user.profile.accepted_tos
                if not has_accepted_tos:
                    return HttpResponseRedirect(reverse("tos-acceptance"))
                else:
                    cache.set(cache_key, 'yes', 2592000)  # 30 days cache
            else:
                # If there is cache it means the terms has been accepted
                pass

        response = self.get_response(request)
        return response


class UpdateEmailHandler(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated \
                and 'tosacceptance' not in request.get_full_path() \
                and 'logout' not in request.get_full_path() \
                and 'tos_api' not in request.get_full_path() \
                and 'tos_web' not in request.get_full_path() \
                and 'contact' not in request.get_full_path() \
                and 'bulklicensechange' not in request.get_full_path() \
                and 'resetemail' not in request.get_full_path() \
                and not request.get_full_path().startswith(settings.MEDIA_URL):
                # replace with dont_redirect() and add resetemail to it after merge with gdpr_acceptance pr

            user = request.user

            if not user.profile.email_is_valid():
                return HttpResponseRedirect(reverse("accounts-email-reset-required"))

        response = self.get_response(request)
        return response
