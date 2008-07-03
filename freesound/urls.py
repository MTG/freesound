# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^$', 'sounds.views.front_page', name='front-page'),
    
    url(r'^account/$', 'accounts.views.home', name="accounts-home"),
    url(r'^account/edit/$', 'accounts.views.edit', name="accounts-edit"),

    url(r'^account/upload/$', 'accounts.views.upload', name="accounts-upload"),
    url(r'^account/describe/$', 'accounts.views.describe', name="accounts-describe"),
    url(r'^account/attribution/$', 'accounts.views.attribution', name="accounts-attribution"),

    url(r'^account/messages/$', 'messages.views.index', name='messages'),
    url(r'^account/messages/(?P<message_id>\d+)/$', 'messages.views.single', name='message'),
    url(r'^account/messages/sent/$', 'messages.views.sent', name='messages-sent'),
    
    url(r'^search/$', 'sounds.views.search', name='sounds-search'),
    
    url(r'^people/$', 'accounts.views.index', name="accounts"),
    url(r'^people/(?P<username>[^//]+)/$', 'accounts.views.single', name="account"),
    url(r'^people/(?P<username>[^//]+)/sounds/$', 'sounds.views.for_user', name="sounds-for-user"),
    url(r'^people/(?P<username>[^//]+)/sounds/(?P<sound_id>\d+)/$', 'sounds.views.single', name="sound"),

    url(r'^people/(?P<username>[^//]+)/packs/$', 'sounds.views.packs_for_user', name="packs-for-user"),
    url(r'^people/(?P<username>[^//]+)/packs/(?P<pack_id>\d+)/$', 'sounds.views.single_pack', name="pack"),

    url(r'^browse/$', 'sounds.views.index', name="sounds"),

    url(r'^browse/tags/(?P<tags>[\w//-]*)$', 'tags.views.index', name="tags"),
    
    url(r'^browse/packs/$', 'sounds.views.packs', name="packs"),
    
    url(r'^browse/random/$', 'sounds.views.random', "sounds-random"),
    url(r'^browse/remixed/$', 'sounds.views.remixed', "sounds-remixed"),
    
    url(r'^browse/geotagged/$', 'geotags.views.index', "geotags"),
    url(r'^browse/geotagged/(?P<sound_id>\d+)/$', 'geotags.views.single', "geotag"),
    
    url(r'^contact/$', 'support.views.contact', "contact"),
    
    url(r'^blog/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://blog.freesound.org/"}, name="blog"),
    
    url(r'^help/$', "django.views.generic.simple.redirect_to", kwargs={'url': "http://help.freesound.org/"}, name="blog"),
    
    (r"^admin/(.*)", admin.site.root),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % settings.MEDIA_URL.strip('/'), 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    )