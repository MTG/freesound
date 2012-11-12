# -*- coding: utf-8 -*-

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

from django.conf.urls.defaults import patterns, url, include, handler404, handler500
from django.contrib import admin
from django.views.generic.simple import direct_to_template
import accounts.views
import geotags.views
import search.views
import sounds.views
import support.views
import tags.views
import forum.views
import comments.views
import bookmarks.views
from django.views.generic.simple import redirect_to

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', sounds.views.front_page, name='front-page'),

    url(r'^people/$', accounts.views.accounts, name="accounts"),
    url(r'^people/(?P<username>[^//]+)/$', accounts.views.account, name="account"),
    url(r'^people/(?P<username>[^//]+)/sounds/$', sounds.views.for_user, name="sounds-for-user"),
    url(r'^people/(?P<username>[^//]+)/flag/$', accounts.views.flag_user, name="flag-user"),
    url(r'^people/(?P<username>[^//]+)/clear_flags/$', accounts.views.clear_flags_user, name="clear-flags-user"),
    url(r'^people/(?P<username>[^//]+)/comments/$', comments.views.for_user, name="comments-for-user"),
    url(r'^people/(?P<username>[^//]+)/geotags/$', geotags.views.for_user, name="geotags-for-user"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/$', sounds.views.sound, name="sound"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/download/.*$', sounds.views.sound_download, name="sound-download"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/flag/$', sounds.views.flag, name="sound-flag"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/edit/sources/$', sounds.views.sound_edit_sources, name="sound-edit-sources"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/edit/$', sounds.views.sound_edit, name="sound-edit"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/remixes/$', sounds.views.remixes, name="sound-remixes"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/geotag/$', sounds.views.geotag, name="sound-geotag"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/delete/$', sounds.views.delete, name="sound-delete"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/similar/$', sounds.views.similar, name="sound-similar"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/downloaders/$', sounds.views.downloaders, name="sound-downloaders"),
    url(r'^people/(?P<username>[^//]+)/packs/$', sounds.views.packs_for_user, name="packs-for-user"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/$', sounds.views.pack, name="pack"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/download/.*$', sounds.views.pack_download, name="pack-download"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/downloaders/$', sounds.views.pack_downloaders, name="pack-downloaders"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/display/$', sounds.views.display_sound_wrapper, name="sound-display"),
    url(r'^people/(?P<username>[^//]+)/downloaded_sounds/$', accounts.views.downloaded_sounds, name="user-downloaded-sounds"),
    url(r'^people/(?P<username>[^//]+)/downloaded_packs/$', accounts.views.downloaded_packs, name="user-downloaded-packs"),
    url(r'^people/(?P<username>[^//]+)/bookmarks/$', bookmarks.views.bookmarks, name="bookmarks-for-user"),
    url(r'^people/(?P<username>[^//]+)/bookmarks/category/(?P<category_id>\d+)/$', bookmarks.views.bookmarks, name="bookmarks-for-user-for-category"),

    url(r'^embed/sound/iframe/(?P<sound_id>\d+)/simple/(?P<player_size>\w+)/$', sounds.views.embed_iframe, name="embed-simple-sound-iframe"),
    url(r'^embed/geotags_box/iframe/$', geotags.views.embed_iframe, name="embed-geotags-box-iframe"),

    url(r'^browse/$', sounds.views.sounds, name="sounds"),
    url(r'^browse/tags/$', tags.views.tags, name="tags"),
    url(r'^browse/tags/(?P<multiple_tags>[\w//-]+)/$', tags.views.tags, name="tags"),
    url(r'^browse/packs/$', sounds.views.packs, name="packs"),
    url(r'^browse/comments/$', comments.views.all, name="comments"),
    url(r'^browse/random/$', sounds.views.random, name="sounds-random"),
    url(r'^browse/geotags/(?P<tag>[\w-]+)?/?$', geotags.views.geotags, name="geotags"),
    url(r'^browse/geotags_box/$', geotags.views.geotags_box, name="geotags-box"),

    url(r'^browse/remixed/$',
        sounds.views.remixed,
        name="remix-groups"),

    url(r'^browse/remixed/(?P<group_id>\d+)/$',
        sounds.views.remix_group,
        name="remix-group"),

    url(r'^contact/', support.views.contact, name="contact"),
    url(r'^search/$', search.views.search, name='sounds-search'),

    (r'^ratings/', include('ratings.urls')),
    (r'^comments/', include('comments.urls')),
    (r'^help/', include('wiki.urls')),
    (r'^forum/', include('forum.urls')),
    (r'^geotags/', include('geotags.urls')),
    (r'^home/', include('accounts.urls')),
    (r'^tickets/', include('tickets.urls')),

    url(r'^blog/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://blog.freesound.org/"}, name="blog"),
    url(r'^crossdomain\.xml$', direct_to_template, kwargs={'template':'crossdomain.xml'}, name="crossdomain"),

    # admin views
    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$', 'general.views.admin_move_ordered_model', name="admin-move"),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', admin.site.urls),

    # api views
    (r'^api/', include('api.urls')),

    # 500 view
    url(r'^crash_me/$',
        accounts.views.crash_me,
        name="crash-me"),

    # old url format redirects
    url(r'^usersViewSingle', accounts.views.old_user_link_redirect, name="old-account-page"),
    url(r'^samplesViewSingle', sounds.views.old_sound_link_redirect, name="old-sound-page"),
    url(r'^packsViewSingle', sounds.views.old_pack_link_redirect, name="old-pack-page"),
    url(r'^tagsViewSingle', tags.views.old_tag_link_redirect, name="old-tag-page"),
    url(r'^forum/viewtopic', forum.views.old_topic_link_redirect, name="old-topic-page"),

    # dead season redirect (THIS IS TEMPORAL)
    url(r'^deadseason/$', redirect_to, {'url': 'http://www.freesound.org/people/Slave2theLight/bookmarks/category/4730/'}),
)

#if you need django to host the admin files...
from django.conf import settings
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        (r'^%s/(?P<path>.*)$' % settings.DATA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.DATA_PATH, 'show_indexes': True}),
    )
