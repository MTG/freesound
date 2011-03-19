from akismet import Akismet
from django.contrib.sites.models import Site
from urllib2 import HTTPError, URLError
from django.conf import settings
from general.models import AkismetSpam

def is_spam(request, comment):
    domain = "http://%s" % Site.objects.get_current().domain
    api = Akismet(key=settings.AKISMET_KEY, blog_url=domain)
    
    data = {
        'user_ip': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'referrer': request.META.get('HTTP_REFERER', ''),
        'comment_type': 'comment',
        'comment_author': request.user.username.encode("utf-8") if request.user.is_authenticated() else '',
    }
    
    if False: # set this to true to force a spam detection
        data['comment_author'] = "viagra-test-123"
    
    try:
        if api.comment_check(comment.encode('utf-8'), data=data, build_data=True):
            if request.user.is_authenticated():
                AkismetSpam.objects.create(user=request.user, spam=comment)
            return True
        else:
            return False
    except HTTPError: # failed to contact akismet...
        return False
    except URLError:
        return False
