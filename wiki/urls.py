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

from django.conf.urls import url
from django.views.generic import TemplateView, RedirectView
import wiki.views as wiki

urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/help/main/"), name="wiki"),
    url(r'^(?P<name>[//\w_-]+)/history/$', wiki.history, name="wiki-page-history"),
    url(r'^(?P<name>[//\w_-]+)/edit/$', wiki.editpage, name="wiki-page-edit"),
    url(r'^(?P<name>[//\w_-]+)/$', wiki.page, name="wiki-page"),
]
