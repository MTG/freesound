from django.shortcuts import render_to_response
from freesound_exceptions import PermissionDenied
from utils.onlineusers import cache_online_users

class PermissionDeniedHandler:
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return render_to_response('permissiondenied.html')
        return None

class OnlineUsersHandler:
    def process_request(self,request):
        cache_online_users(request)
        return None
