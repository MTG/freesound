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
    url(r'^sounds/(?P<sound_id>\d+)/?$',                             AR(SoundHandler),       name='api-single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/(?P<file_or_preview>\w+)/?$',    AR(SoundServeHandler),  name='api-sound-serve'),
    # users
    url(r'^people/(?P<username>[^//]+)/?$',                          AR(UserHandler),        name='api-single-user'),
    url(r'^people/(?P<username>[^//]+)/sounds/?$',                   AR(UserSoundsHandler),  name='api-user-sounds'),
    url(r'^people/(?P<username>[^//]+)/packs/?$',                    AR(UserPacksHandler),   name='api-user-packs'),
    # packs
    url(r'^packs/(?P<pack_id>\d+)/?$',                               AR(PackHandler),        name='api-single-pack'),
    url(r'^packs/(?P<pack_id>\d+)/serve/?$',                         AR(PackServeHandler),   name='api-pack-serve'),
    url(r'^packs/(?P<pack_id>\d+)/sounds/?$',                        AR(PackSoundsHandler),  name='api-pack-sounds'),

   # website
    url(r'^apply/?$', create_api_key),
)
