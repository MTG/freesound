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
            and not request.get_full_path().startswith(settings.MEDIA_URL):

            user = request.user
            cache_key = "has-old-license-%s" % user.id
            cache_info = cache.get(cache_key)
            
            if cache_info == None or 0 or not isinstance(cache_info, (list, tuple)):
                has_old_license = user.profile.has_old_license
                has_sounds = Sound.objects.filter(user=user).exists()
                cache.set(cache_key, [has_old_license, has_sounds], 2592000) # 30 days cache
            else :
                has_old_license = cache_info[0] 
                has_sounds = cache_info[1]
                #print "CACHE LICENSE: has_old_license=" + str(has_old_license) + " has_sounds=" + str(has_sounds)
                if has_old_license and has_sounds:
                    return HttpResponseRedirect(reverse("bulk-license-change"))
