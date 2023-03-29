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

import os

from django.urls import path, re_path, include
from django.contrib import admin
from django.views.generic import TemplateView, RedirectView
import accounts.views
import geotags.views
import search.views
import sounds.views
import support.views
import tags.views
import forum.views
import comments.views
import bookmarks.views
import follow.views
import general.views
import donations.views
import utils.tagrecommendation_utilities as tagrec
from apiv2.apiv2_utils import apiv1_end_of_life_message

admin.autodiscover()

urlpatterns = [
    path('', sounds.views.front_page, name='front-page'),

    path('people/', accounts.views.accounts, name="accounts"),
    path('people/<username>/', accounts.views.account, name="account"),
    path('people/<username>/sounds/', sounds.views.for_user, name="sounds-for-user"),
    path('people/<username>/flag/', accounts.views.flag_user, name="flag-user"),
    path('people/<username>/clear_flags/', accounts.views.clear_flags_user, name="clear-flags-user"),
    path('people/<username>/comments/', comments.views.for_user, name="comments-for-user"),
    path('people/<username>/comments_by/', comments.views.by_user, name="comments-by-user"),
    path('people/<username>/geotags/', geotags.views.for_user, name="geotags-for-user"),
    path('people/<username>/sounds/<int:sound_id>/', sounds.views.sound, name="sound"),
    re_path(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/download/.*$', sounds.views.sound_download, name="sound-download"),
    path('people/<username>/sounds/<int:sound_id>/flag/', sounds.views.flag, name="sound-flag"),
    path('people/<username>/sounds/<int:sound_id>/edit/sources/', sounds.views.sound_edit_sources, name="sound-edit-sources"),
    path('people/<username>/sounds/<int:sound_id>/edit/', sounds.views.sound_edit, name="sound-edit"),
    path('people/<username>/sounds/<int:sound_id>/remixes/', sounds.views.remixes, name="sound-remixes"),
    path('people/<username>/sounds/<int:sound_id>/geotag/', geotags.views.for_sound, name="sound-geotag"),
    path('people/<username>/sounds/<int:sound_id>/delete/', sounds.views.delete, name="sound-delete"),
    path('people/<username>/sounds/<int:sound_id>/similar/', sounds.views.similar, name="sound-similar"),
    path('people/<username>/sounds/<int:sound_id>/downloaders/', sounds.views.downloaders, name="sound-downloaders"),
    path('people/<username>/packs/', sounds.views.packs_for_user, name="packs-for-user"),
    path('people/<username>/packs/<int:pack_id>/', sounds.views.pack, name="pack"),
    path('people/<username>/packs/<int:pack_id>/edit/', sounds.views.pack_edit, name="pack-edit"),
    path('people/<username>/packs/<int:pack_id>/delete/', sounds.views.pack_delete, name="pack-delete"),
    re_path(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/download/.*$', sounds.views.pack_download, name="pack-download"),
    path('people/<username>/packs/<int:pack_id>/downloaders/', sounds.views.pack_downloaders, name="pack-downloaders"),
    path('people/<username>/packs/<int:pack_id>/licenses/', sounds.views.pack_licenses, name="pack-licenses"),
    path('people/<username>/sounds/<int:sound_id>/display/', sounds.views.display_sound_wrapper, name="sound-display"),
    path('people/<username>/downloaded_sounds/', accounts.views.downloaded_sounds, name="user-downloaded-sounds"),
    path('people/<username>/downloaded_packs/', accounts.views.downloaded_packs, name="user-downloaded-packs"),
    path('people/<username>/bookmarks/', bookmarks.views.bookmarks_for_user, name="bookmarks-for-user"),
    path('people/<username>/bookmarks/category/<int:category_id>/', bookmarks.views.bookmarks_for_user, name="bookmarks-for-user-for-category"),
    path('people/<username>/following_users/', follow.views.following_users, name="user-following-users"),
    path('people/<username>/followers/', follow.views.followers, name="user-followers"),
    path('people/<username>/following_tags/', follow.views.following_tags, name="user-following-tags"),

    path('charts/', accounts.views.charts, name="charts"),  # BW only

    path('embed/sound/iframe/<int:sound_id>/simple/<player_size>/', sounds.views.embed_iframe, name="embed-simple-sound-iframe"),
    path('embed/geotags_box/iframe/', geotags.views.embed_iframe, name="embed-geotags-box-iframe"),
    path('oembed/', sounds.views.oembed, name="oembed-sound"),

    path('after-download-modal/', sounds.views.after_download_modal, name="after-download-modal"),

    path('browse/', sounds.views.sounds, name="sounds"),
    path('browse/tags/', tags.views.tags, name="tags"),
    re_path(r'^browse/tags/(?P<multiple_tags>[\w//-]+)/$', tags.views.tags, name="tags"),
    path('browse/packs/', sounds.views.packs, name="packs"),
    path('browse/comments/', comments.views.all, name="comments"),
    path('browse/random/', sounds.views.random, name="sounds-random"),
    re_path(r'^browse/geotags/(?P<tag>[\w-]+)?/?$', geotags.views.geotags, name="geotags"),
    path('browse/geotags_box/', geotags.views.geotags_box, name="geotags-box"),

    path('browse/remixed/', sounds.views.remixed, name="remix-groups"),
    path('browse/remixed/<int:group_id>/', sounds.views.remix_group, name="remix-group"),

    path('contact/', support.views.contact, name="contact"),

    path('search/', search.views.search, name='sounds-search'),
    path('clustering_facet/', search.views.clustering_facet, name='clustering-facet'),
    path('clustered_graph/', search.views.clustered_graph, name='clustered-graph-json'),
    path('query_suggestions/', search.views.query_suggestions, name='query-suggestions'),

    path('add_sounds_modal/sources/', sounds.views.add_sounds_modal_for_edit_sources, name="add-sounds-modal-sources"),
    path('add_sounds_modal/pack/<int:pack_id>/', sounds.views.add_sounds_modal_for_pack_edit, name="add-sounds-modal-pack"),
    
    path('', include('ratings.urls')),
    path('comments/', include('comments.urls')),
    path('help/', include('wiki.urls')),
    path('forum/', include('forum.urls')),
    path('geotags/', include('geotags.urls')),
    path('home/', include('accounts.urls')),
    path('donations/', include('donations.urls')),
    path('tickets/', include('tickets.urls')),
    path('monitor/', include('monitor.urls')),
    path('follow/', include('follow.urls')),

    path('blog/', RedirectView.as_view(url='https://blog.freesound.org/'), name="blog"),
    re_path(r'^crossdomain\.xml$', TemplateView.as_view(template_name='crossdomain.xml'), name="crossdomain"),

    # admin views
    re_path(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$',
            general.views.admin_move_ordered_model, name="admin-move"),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),

    # api views
    path('api/', apiv1_end_of_life_message),
    path('apiv2/', include('apiv2.urls')),

    # tag recommendation
    path('tagrecommendation/recommendtags/', tagrec.get_recommended_tags_view, name="recommend-tags"),

    # 500 view
    path('crash_me/', accounts.views.crash_me, name="crash-me"),

    path('donate/', donations.views.donate_redirect, name="donate-redirect"),
    path('s/<int:sound_id>/', sounds.views.sound_short_link, name="short-sound-link"),
    path('p/<int:pack_id>/', sounds.views.pack_short_link, name="short-pack-link"),

    # old url format redirects
    re_path(r'^usersViewSingle', accounts.views.old_user_link_redirect, name="old-account-page"),
    re_path(r'^samplesViewSingle', sounds.views.old_sound_link_redirect, name="old-sound-page"),
    re_path(r'^packsViewSingle', sounds.views.old_pack_link_redirect, name="old-pack-page"),
    re_path(r'^tagsViewSingle', tags.views.old_tag_link_redirect, name="old-tag-page"),
    re_path(r'^forum/viewtopic', forum.views.old_topic_link_redirect, name="old-topic-page"),
]

urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]

# if you need django to host the admin files...
from django.conf import settings
from django.views.static import serve
if settings.DEBUG:
    import debug_toolbar

    def serve_source_map_files(request):
        path = request.path
        document_root = os.path.join(os.path.dirname(__file__), 'static', 'bw-frontend', 'dist')
        return serve(request, path, document_root=document_root, show_indexes=False)

    urlpatterns += [
        re_path(r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), serve,
                {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        re_path(r'^%s/(?P<path>.*)$' % settings.DATA_URL.strip('/'), serve,
                {'document_root': settings.DATA_PATH, 'show_indexes': True}),
        path('__debug__/', include(debug_toolbar.urls)),
        re_path(r'^.*\.map$', serve_source_map_files),
    ]
