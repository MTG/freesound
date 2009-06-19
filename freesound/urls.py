# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'sounds.views.front_page', name='front-page'),
    
    url(r'^people/$', 'accounts.views.accounts', name="accounts"),
    url(r'^people/(?P<username>[^//]+)/$', 'accounts.views.account', name="account"),
    url(r'^people/(?P<username>[^//]+)/sounds/$', 'sounds.views.for_user', name="sounds-for-user"),
    url(r'^people/(?P<username>[^//]+)/geotags/$', 'geotags.views.for_user', name="geotags-for-user"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/$', 'sounds.views.sound', name="sound"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/remixes/$', 'sounds.views.remixes', name="sound-remixes"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/sources/$', 'sounds.views.sources', name="sound-sources"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/geotag/$', 'sounds.views.geotag', name="sound-geotag"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/similar/$', 'sounds.views.similar', name="sound-similar"),
    url(r'^people/(?P<username>[^//]+)/packs/$', 'sounds.views.packs_for_user', name="packs-for-user"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/$', 'sounds.views.pack', name="pack"),

    url(r'^browse/$', 'sounds.views.sounds', name="sounds"),
    url(r'^browse/tags/(?P<multiple_tags>[\w//-]*)/$', 'tags.views.tags', name="tags"),
    url(r'^browse/packs/$', 'sounds.views.packs', name="packs"),
    url(r'^browse/random/$', 'sounds.views.random', name="sounds-random"),
    url(r'^browse/remixed/$', 'sounds.views.remixed', name="sounds-remixed"),
    url(r'^browse/geotagged/$', 'geotags.views.geotags', name="geotags"),
    
    url(r'^contact/', 'support.views.contact', name="contact"),

    url(r'^search/$', 'sounds.views.search', name='sounds-search'),
    
    (r'^ratings/', include('ratings.urls')),
    (r'^help/', include('wiki.urls')),
    (r'^forum/', include('forum.urls')),
    (r'^geotags/', include('geotags.urls')),
    (r'^account/', include('accounts.urls')),
    
    url(r'^blog/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://blog.freesound.org/"}, name="blog"),

    # admin views
    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$', 'general.views.admin_move_ordered_model', name="admin-move"),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )
