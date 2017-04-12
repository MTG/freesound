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
from follow import views

urlpatterns = [
    url(r'^follow_user/(?P<username>[^//]+)/$', views.follow_user, name='follow-user'),
    url(r'^unfollow_user/(?P<username>[^//]+)/$', views.unfollow_user, name='unfollow-user'),
    url(r'^follow_tags/(?P<slash_tags>[\w//-]+)/$', views.follow_tags, name='follow-tags'),
    url(r'^unfollow_tags/(?P<slash_tags>[\w//-]+)/$', views.unfollow_tags, name='unfollow-tags'),
]
