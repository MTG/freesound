# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
import views as wiki

urlpatterns = patterns('',
    url(r'^$', "django.views.generic.simple.redirect_to", kwargs={'url': "/help/main/"}, name="wiki"),
    url(r'^(?P<name>[//\w_-]+)/edit/$', wiki.editpage, name="wiki-page-edit"),
    url(r'^(?P<name>[//\w_-]+)/$', wiki.page, name="wiki-page"),
)