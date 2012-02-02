import models
from django.http import HttpResponseForbidden

class StopForumSpamMiddleware():

    def process_request(self, request):

        if not request.method == 'POST':
            return

        if request.path.startswith("/home") or request.path.startswith("/forum"):
            return self.check_request_ip(request)
    
    def check_request_ip(self, request):
        
        remote_ip = request.META['REMOTE_ADDR']
        
        if models.Cache.objects.filter(ip=remote_ip).count() > 0:
            return HttpResponseForbidden("We have detected you as being a possible spammer. If you think this is not correct, please contact us at support at this domain.")
    
