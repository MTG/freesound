from piston.utils import rc
from models import ApiKey

# vincent_akkermans: 0b7e9005d29c4e03b1ffc0f385060a5f

class KeyAuthentication():
    
    def __init__(self, get_parameter='api_key'):
        self.get_parameter = get_parameter

    def is_authenticated(self, request):
        api_key = request.GET.get(self.get_parameter, False)
        if not api_key:
            return False
        try:
            db_api_key = ApiKey.objects.get(key=api_key, status='approved')
        except ApiKey.DoesNotExist:
            return False
        request.user = db_api_key.user                
        return True
        
    def challenge(self):
        resp = rc.FORBIDDEN
        resp.content = 'Please include your api key as the %s GET/POST parameter.\n' % self.get_parameter
        return resp

