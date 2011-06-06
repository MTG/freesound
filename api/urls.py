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
    url(r'^sounds/search/?$',                                        AR(SoundSearchHandler),         name='api-search'),
    url(r'^sounds/(?P<sound_id>\d+)/?$',                             AR(SoundHandler),               name='api-single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis/?$',                    AR(SoundAnalysisHandler),       name='api-sound-analysis'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis(?P<filter>/[\w\/]+)/?$',AR(SoundAnalysisHandler),       name='api-sound-analysis-filtered'),
    # For future use (when we serve analysis files through autenthication)
    #url(r'^sounds/(?P<sound_id>\d+)/analysis_frames/?$',             AR(SoundAnalysisFramesHandler), name='api-sound-analysis-frames'),    
    url(r'^sounds/(?P<sound_id>\d+)/serve/?$',                       AR(SoundServeHandler),          name='api-sound-serve'),
    url(r'^sounds/(?P<sound_id>\d+)/similar/?$',                     AR(SoundSimilarityHandler),     name='api-sound-similarity'),
    
    # users
    url(r'^people/(?P<username>[^//]+)/?$',                          AR(UserHandler),           name='api-single-user'),
    url(r'^people/(?P<username>[^//]+)/sounds/?$',                   AR(UserSoundsHandler),     name='api-user-sounds'),
    url(r'^people/(?P<username>[^//]+)/packs/?$',                    AR(UserPacksHandler),      name='api-user-packs'),
    
    # packs
    url(r'^packs/(?P<pack_id>\d+)/?$',                               AR(PackHandler),           name='api-single-pack'),
    url(r'^packs/(?P<pack_id>\d+)/serve/?$',                         AR(PackServeHandler),      name='api-pack-serve'),
    url(r'^packs/(?P<pack_id>\d+)/sounds/?$',                        AR(PackSoundsHandler),     name='api-pack-sounds'),

    # website
    url(r'^apply/?$', create_api_key),
)


