#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.conf.urls import *
from piston.resource import Resource
from handlers import *
from api_utils import build_invalid_url
from django.conf import settings

if not settings.APIV2KEYS_ALLOWED_FOR_APIV1:
    from views import create_api_key as apply_for_api_key_view
else:
    from apiv2.views import create_apiv2_key as apply_for_api_key_view



class AR(Resource):
    def __call__(self, *args, **kwargs):
        response = super(AR, self).__call__(*args, **kwargs)
        response['Access-Control-Allow-Origin'] = '*'
        return response

urlpatterns = patterns('',
    # sounds
    url(r'^sounds/search/$',                                        AR(SoundSearchHandler),         name='api-search'),
    url(r'^sounds/content_search/$',                                AR(SoundContentSearchHandler),  name='api-content-search'),
    url(r'^sounds/(?P<sound_id>\d+)/$',                             AR(SoundHandler),               name='api-single-sound'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis/$',                    AR(SoundAnalysisHandler),       name='api-sound-analysis'),
    url(r'^sounds/(?P<sound_id>\d+)/analysis(?P<filter>/[\w\/]+)/$',AR(SoundAnalysisHandler),       name='api-sound-analysis-filtered'),
    # For future use (when we serve analysis files through autenthication)
    #url(r'^sounds/(?P<sound_id>\d+)/analysis_frames/$',            AR(SoundAnalysisFramesHandler), name='api-sound-analysis-frames'),
    url(r'^sounds/(?P<sound_id>\d+)/serve/$',                       AR(SoundServeHandler),          name='api-sound-serve'),
    url(r'^sounds/(?P<sound_id>\d+)/previews/(?P<filename>[^//]+)/$', AR(SoundPreviewHandler),      name='api-sound-preview'),
    url(r'^sounds/(?P<sound_id>\d+)/similar/$',                     AR(SoundSimilarityHandler),     name='api-sound-similarity'),
    url(r'^sounds/geotag/$',                                        AR(SoundGeotagHandler),         name='api-sound-geotag'),
    
    # users
    url(r'^people/(?P<username>[^//]+)/$',                                                     AR(UserHandler),                    name='api-single-user'),
    url(r'^people/(?P<username>[^//]+)/sounds/$',                                              AR(UserSoundsHandler),              name='api-user-sounds'),
    url(r'^people/(?P<username>[^//]+)/packs/$',                                               AR(UserPacksHandler),               name='api-user-packs'),
    url(r'^people/(?P<username>[^//]+)/bookmark_categories/$',                                 AR(UserBookmarkCategoriesHandler),  name='api-user-bookmark-categories'),
    url(r'^people/(?P<username>[^//]+)/bookmark_categories/(?P<category_id>\d+)/sounds/$',     AR(UserBookmarkCategoryHandler),    name='api-user-bookmark-category'),
    url(r'^people/(?P<username>[^//]+)/bookmark_categories/uncategorized/sounds/$',            AR(UserBookmarkCategoryHandler),    name='api-user-bookmark-uncategorized'),

    # packs
    url(r'^packs/(?P<pack_id>\d+)/$',                               AR(PackHandler),           name='api-single-pack'),
    url(r'^packs/(?P<pack_id>\d+)/serve/$',                         AR(PackServeHandler),      name='api-pack-serve'),
    url(r'^packs/(?P<pack_id>\d+)/sounds/$',                        AR(PackSoundsHandler),     name='api-pack-sounds'),

    # cc-mixter pool
    url(r'^pool/search$',                                           SoundPoolSearchHandler(),   name='api-pool-search'),
    url(r'^pool/search/$',                                          SoundPoolSearchHandler(),   name='api-pool-search-slash'),
    url(r'^pool/info$',                                             SoundPoolInfoHandler(),     name='api-pool-info'),
    url(r'^pool/info/$',                                            SoundPoolInfoHandler(),     name='api-pool-info-slash'),
    
    # website
    url(r'^apply/$', apply_for_api_key_view),

    # anything else (invalid urls)
    url(r'/$', build_invalid_url ),
)


