from django.conf.urls.defaults import *
from piston.resource import Resource
from handlers import *
from views import create_api_key
from key_authentication import KeyAuthentication

auth = KeyAuthentication()

class AR(Resource):
    ''' Uses the standard authentication mechanism '''
    def __init__(self, handler, authentication=auth):
        super(AR, self).__init__(handler, authentication)

urlpatterns = patterns('',
    # sounds
    url(r'^sounds/search/?$',                                        AR(SoundSearchHandler), name='api-search'),
    url(r'^sounds/(?P<sound_id>\d+)/?$',                             AR(SoundHandler),       name='single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/(?P<file_or_preview>\w+)/?$',    AR(SoundServeHandler),  name='sound-serve'),
    # users
    url(r'^people/(?P<username>[\w_-]+)/?$',                         AR(UserHandler),        name='single-user'),
    url(r'^people/(?P<username>[\w_-]+)/sounds/?$',                  AR(UserSoundsHandler),  name='user-sounds'),
    url(r'^people/(?P<username>[\w_-]+)/packs/?$',                   AR(UserPacksHandler),   name='user-packs'),
    
   # url(r'^update_solr/?$',                                             CsrfExemptResource(UpdateSolrHandler)),
   # website
    url(r'^apply/?$', create_api_key),
)