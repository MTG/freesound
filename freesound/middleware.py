from django.shortcuts import render_to_response
from freesound_exceptions import PermissionDenied

class PermissionDeniedHandler:
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return render_to_response('permissiondenied.html')
        return None