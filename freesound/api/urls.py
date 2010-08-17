from django.conf.urls.defaults import *
from piston.resource import Resource
from handlers import *

class CsrfExemptResource(Resource):
            """A Custom Resource that is csrf exempt"""
            def __init__(self, handler, authentication=None):
                super(CsrfExemptResource, self).__init__(handler, authentication)
                self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)


urlpatterns = patterns('',

    # sounds
    url(r'^sounds/search/?$',                                            CsrfExemptResource(SoundSearchHandler)),
    url(r'^sounds/(?P<sound_id>\d+)/?$',                                 CsrfExemptResource(SoundHandler)),
    url(r'^sounds/(?P<sound_id>\d+)/(?P<file_or_preview>\w+)/?$',        CsrfExemptResource(SoundServeHandler)),
    # users
    url(r'^people/(?P<username>[\w_-]+)/?$',                             CsrfExemptResource(UserHandler)),
    url(r'^people/(?P<username>[\w_-]+)/sounds/?$',                      CsrfExemptResource(UserSoundsHandler)),
    url(r'^people/(?P<username>[\w_-]+)/packs/?$',                       CsrfExemptResource(UserPacksHandler)),
    
   # url(r'^update_solr/?$',                                             CsrfExemptResource(UpdateSolrHandler)),
)