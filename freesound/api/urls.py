from django.conf.urls.defaults import *
from piston.resource import Resource
from handlers import *
from views import create_api_key
from key_authentication import KeyAuthentication

auth = KeyAuthentication()

class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=auth):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

urlpatterns = patterns('',
    # sounds
    url(r'^sounds/search/?$',                                        CsrfExemptResource(SoundSearchHandler), name='api-search'),
    url(r'^sounds/(?P<sound_id>\d+)/?$',                             CsrfExemptResource(SoundHandler),       name='single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/(?P<file_or_preview>\w+)/?$',    CsrfExemptResource(SoundServeHandler),  name='sound-serve'),
    # users
    url(r'^people/(?P<username>[\w_-]+)/?$',                         CsrfExemptResource(UserHandler),        name='single-user'),
    url(r'^people/(?P<username>[\w_-]+)/sounds/?$',                  CsrfExemptResource(UserSoundsHandler),  name='user-sounds'),
    url(r'^people/(?P<username>[\w_-]+)/packs/?$',                   CsrfExemptResource(UserPacksHandler),   name='user-packs'),
    
   # url(r'^update_solr/?$',                                             CsrfExemptResource(UpdateSolrHandler)),
   # website
    url(r'^apply/?$', create_api_key),
)