# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
import wiki.views as wiki

urlpatterns = patterns('',
    url(r'^$', "django.views.generic.simple.redirect_to", kwargs={'url': "/help/main/"}, name="wiki"),
    url(r'^$', "django.views.generic.simple.redirect_to", kwargs={'url': "/help/developers/"}, name="wiki_developers"),
    url(r'^(?P<name>[//\w_-]+)/history/$', wiki.history, name="wiki-page-history"),
    url(r'^(?P<name>[//\w_-]+)/edit/$', wiki.editpage, name="wiki-page-edit"),
    url(r'^(?P<name>[//\w_-]+)/$', wiki.page, name="wiki-page"),
)