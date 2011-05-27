from django.shortcuts import render_to_response
from freesound_exceptions import PermissionDenied
from django.contrib.auth.models import User
from accounts.models import Profile
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
# from django.template import RequestContext
from django.conf import settings
from django.core.cache import cache


class PermissionDeniedHandler:
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return render_to_response('permissiondenied.html')
        return None
    
class BulkChangeLicenseHandler:
    def process_request(self, request):
        # check for authentication,
        # avoid infinite loop
        # allow user to logout (maybe a bit too much...)
        # don't run it for media urls.
        # N.B. probably better just to check for login in the URL
        if request.user.is_authenticated() \
            and not 'bulklicensechange' in request.get_full_path() \
            and not 'logout' in request.get_full_path() \
            and not request.get_full_path().startswith(settings.MEDIA_URL):
            
            user = request.user
            cache_key = "has-old-license-%s" % user.id
            has_old_license = cache.get(cache_key)
            
            if has_old_license == None:
                has_old_license = user.profile.has_old_license
                cache.set(cache_key, has_old_license, 2592000) # 30 days cache

            if has_old_license:
                return HttpResponseRedirect(reverse("bulk-license-change", args=[request.user.username]))
              
        return None