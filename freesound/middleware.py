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

import json
import logging

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from utils.onlineusers import cache_online_users

web_logger = logging.getLogger('web')


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
            if user.profile.has_old_license:
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
            selected_ui = request.GET.get(settings.FRONTEND_CHOOSER_REQ_PARAM_NAME)
            current_ui = request.session.get(settings.FRONTEND_SESSION_PARAM_NAME, None)
            if selected_ui != current_ui:
                web_logger.info('Frontend activation (%s)' % json.dumps({'name': selected_ui,
                                                                         'username': request.user.username}))
            request.session[settings.FRONTEND_SESSION_PARAM_NAME] = selected_ui
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
            if not user.profile.accepted_tos:
                return HttpResponseRedirect(reverse("tos-acceptance"))

        response = self.get_response(request)
        return response


class UpdateEmailHandler(object):
    message = "We have identified that some emails that we have sent to you didn't go through, thus it appears that " \
              "your email address is not valid. Please update your email address to a working one to continue using " \
              "Freesound"

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
                messages.add_message(request, messages.INFO, self.message)
                return HttpResponseRedirect(reverse("accounts-email-reset"))

        response = self.get_response(request)
        return response
