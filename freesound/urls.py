# -*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin
from django.views.generic.simple import direct_to_template
import accounts.views
import geotags.views
import search.views
import sounds.views
import support.views
import tags.views

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', sounds.views.front_page, name='front-page'),
    
    url(r'^people/$', accounts.views.accounts, name="accounts"),
    url(r'^people/(?P<username>[^//]+)/$', accounts.views.account, name="account"),
    url(r'^people/(?P<username>[^//]+)/sounds/$', sounds.views.for_user, name="sounds-for-user"),
    url(r'^people/(?P<username>[^//]+)/geotags/$', geotags.views.for_user, name="geotags-for-user"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/$', sounds.views.sound, name="sound"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/download/.*$', sounds.views.sound_download, name="sound-download"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/flag/$', sounds.views.flag, name="sound-flag"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/edit/$', sounds.views.sound_edit, name="sound-edit"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/remixes/$', sounds.views.remixes, name="sound-remixes"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/sources/$', sounds.views.sources, name="sound-sources"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/geotag/$', sounds.views.geotag, name="sound-geotag"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/similar/$', sounds.views.similar, name="sound-similar"),
    url(r'^people/(?P<username>[^//]+)/packs/$', sounds.views.packs_for_user, name="packs-for-user"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/$', sounds.views.pack, name="pack"),

    url(r'^browse/$', sounds.views.sounds, name="sounds"),
    url(r'^browse/tags/$', tags.views.tags, name="tags"),
    url(r'^browse/tags/(?P<multiple_tags>[\w//-]+)/$', tags.views.tags, name="tags"),
    url(r'^browse/packs/$', sounds.views.packs, name="packs"),
    url(r'^browse/random/$', sounds.views.random, name="sounds-random"),
    url(r'^browse/remixed/$', sounds.views.remixed, name="sounds-remixed"),
    url(r'^browse/geotags/(?P<tag>[\w-]+)?/?$', geotags.views.geotags, name="geotags"),
    
    url(r'^contact/', support.views.contact, name="contact"),

    url(r'^search/$', search.views.search, name='sounds-search'),
    
    (r'^ratings/', include('ratings.urls')),
    (r'^help/', include('wiki.urls')),
    (r'^forum/', include('forum.urls')),
    (r'^geotags/', include('geotags.urls')),
    (r'^home/', include('accounts.urls')),
    
    url(r'^blog/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://blog.freesound.org/"}, name="blog"),
    url(r'^crossdomain\.xml$', direct_to_template, kwargs={'template':'crossdomain.xml'}, name="crossdomain"),

    # admin views
    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$', 'general.views.admin_move_ordered_model', name="admin-move"),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
)

#if you need django to host the admin files...
#from django.conf import settings
#if settings.DEBUG:
#    urlpatterns += patterns('',
#        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
#    )
