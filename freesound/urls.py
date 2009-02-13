# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'sounds.views.front_page', name='front-page'),
    
    (r'^account/', include('accounts.urls')),
    
    url(r'^search/$', 'sounds.views.search', name='sounds-search'),
    
    url(r'^people/$', 'accounts.views.accounts', name="accounts"),
    url(r'^people/(?P<username>[^//]+)/$', 'accounts.views.account', name="account"),
    url(r'^people/(?P<username>[^//]+)/sounds/$', 'sounds.views.for_user', name="sounds-for-user"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/$', 'sounds.views.sound', name="sound"),

    url(r'^people/(?P<username>[^//]+)/packs/$', 'sounds.views.packs_for_user', name="packs-for-user"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/$', 'sounds.views.pack', name="pack"),

    url(r'^browse/$', 'sounds.views.sounds', name="sounds"),

    url(r'^browse/tags/(?P<multiple_tags>[\w//-]*)/$', 'tags.views.tags', name="tags"),
    
    url(r'^browse/packs/$', 'sounds.views.packs', name="packs"),
    
    url(r'^browse/random/$', 'sounds.views.random', "sounds-random"),
    url(r'^browse/remixed/$', 'sounds.views.remixed', "sounds-remixed"),
    
    url(r'^browse/geotagged/$', 'geotags.views.geotags', "geotags"),
    url(r'^browse/geotagged/(?P<sound_id>\d+)/$', 'geotags.views.geotag', "geotag"),
    
    url(r'^contact/$', 'support.views.contact', "contact"),
    
    url(r'^blog/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://blog.freesound.org/"}, name="blog"),
    
    url(r'^help/$', "django.views.generic.simple.redirect_to", kwargs={'url': "/help/main/"}, name="wiki"),
    url(r'^help/(?P<name>\w+)/$', 'wiki.views.page', name="wiki-page"),
    url(r'^help/(?P<name>\w+)/edit/$', 'wiki.views.editpage', name="wiki-page-edit"),

    (r'^forum/', include('forum.urls')),

    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$', 'general.views.admin_move_ordered_model', name="admin-move"),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )
