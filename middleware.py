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

from django.shortcuts import render_to_response
from freesound_exceptions import PermissionDenied
from utils.onlineusers import cache_online_users
from django.contrib.auth.models import User
from accounts.models import Profile
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
# from django.template import RequestContext
from django.conf import settings
from django.core.cache import cache
from sounds.models import Sound


class PermissionDeniedHandler:
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return render_to_response('permissiondenied.html')
        return None

class OnlineUsersHandler:
    def process_request(self,request):
        cache_online_users(request)
        return None

class CheckIfRequestIsHttps:
    def process_request(self,request):
        # header HTTP_X_FORWARDED_PROTOCOL is set by nginx in loadbalancer
        forwarded_protocol = request.META.get('HTTP_X_FORWARDED_PROTOCOL', None)
        if forwarded_protocol == 'https':
            request.using_https = True
        else:
            request.using_https = False
        # monkey patch request.is_secure()
        request.is_secure = lambda: request.using_https
        return None

class BulkChangeLicenseHandler:
    def process_request(self, request):
        # check for authentication,
        # avoid infinite loop
        # allow user to logout (maybe a bit too much...)
        # don't run it for media URLs
        # N.B. probably better just to check for login in the URL
        if request.user.is_authenticated() \
            and not 'bulklicensechange' in request.get_full_path() \
            and not 'logout' in request.get_full_path() \
            and not 'tosacceptance' in request.get_full_path() \
            and not request.get_full_path().startswith(settings.MEDIA_URL):

            user = request.user
            cache_key = "has-old-license-%s" % user.id
            cache_info = cache.get(cache_key)
            
            if cache_info == None or 0 or not isinstance(cache_info, (list, tuple)):
                has_old_license = user.profile.has_old_license
                has_sounds = Sound.objects.filter(user=user).exists()
                cache.set(cache_key, [has_old_license, has_sounds], 2592000) # 30 days cache
                if has_old_license and has_sounds:
                    return HttpResponseRedirect(reverse("bulk-license-change"))
                
            else :
                has_old_license = cache_info[0] 
                has_sounds = cache_info[1]
                #print "CACHE LICENSE: has_old_license=" + str(has_old_license) + " has_sounds=" + str(has_sounds)
                if has_old_license and has_sounds:
                    return HttpResponseRedirect(reverse("bulk-license-change"))


class TosAcceptanceHandler:
    def process_request(self, request):

        if request.user.is_authenticated() \
            and not 'tosacceptance' in request.get_full_path() \
            and not 'logout' in request.get_full_path() \
            and not 'tos_api' in request.get_full_path() \
            and not 'tos_web' in request.get_full_path() \
            and not 'contact' in request.get_full_path() \
            and not 'bulklicensechange' in request.get_full_path() \
            and not request.get_full_path().startswith(settings.MEDIA_URL):

            user = request.user
            cache_key = "has-accepted-tos-%s" % user.id
            cache_info = cache.get(cache_key)
            
            if not cache_info:
                has_accepted_tos = user.profile.accepted_tos
                if not has_accepted_tos:
                    return HttpResponseRedirect(reverse("tos-acceptance"))
                else:
                    cache.set(cache_key, 'yes', 2592000) # 30 days cache
            else:
                # If there is cache it means the terms has been accepted
                pass
