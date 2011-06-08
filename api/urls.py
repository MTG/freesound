from django.conf.urls.defaults import *
from piston.resource import Resource
from handlers import *
from views import create_api_key
#from key_authentication import KeyAuthentication

#auth = KeyAuthentication()

#class AR(Resource):
#    ''' Uses the standard authentication mechanism '''
#    def __init__(self, handler, authentication=auth):
#        super(AR, self).__init__(handler, authentication)

urlpatterns = patterns('',
    # sounds
    url(r'^sounds/search/?$',                                        Resource(SoundSearchHandler),         name='api-search'),
    url(r'^sounds/(?P<sound_id>\d+)/?$',                             Resource(SoundHandler),               name='api-single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis/?$',                    Resource(SoundAnalysisHandler),       name='api-sound-analysis'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis(?P<filter>/[\w\/]+)/?$',Resource(SoundAnalysisHandler),       name='api-sound-analysis-filtered'),
    # For future use (when we serve analysis files through autenthication)
    #url(r'^sounds/(?P<sound_id>\d+)/analysis_frames/?$',            Resource(SoundAnalysisFramesHandler), name='api-sound-analysis-frames'),    
    url(r'^sounds/(?P<sound_id>\d+)/serve/?$',                       Resource(SoundServeHandler),          name='api-sound-serve'),
    url(r'^sounds/(?P<sound_id>\d+)/similar/?$',                     Resource(SoundSimilarityHandler),     name='api-sound-similarity'),
    
    # users
    url(r'^people/(?P<username>[^//]+)/?$',                          Resource(UserHandler),           name='api-single-user'),
    url(r'^people/(?P<username>[^//]+)/sounds/?$',                   Resource(UserSoundsHandler),     name='api-user-sounds'),
    url(r'^people/(?P<username>[^//]+)/packs/?$',                    Resource(UserPacksHandler),      name='api-user-packs'),
    
    # packs
    url(r'^packs/(?P<pack_id>\d+)/?$',                               Resource(PackHandler),           name='api-single-pack'),
    url(r'^packs/(?P<pack_id>\d+)/serve/?$',                         Resource(PackServeHandler),      name='api-pack-serve'),
    url(r'^packs/(?P<pack_id>\d+)/sounds/?$',                        Resource(PackSoundsHandler),     name='api-pack-sounds'),

    # website
    url(r'^apply/?$', create_api_key),
)


