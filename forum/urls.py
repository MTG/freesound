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

from django.urls import path, re_path
import forum.views as forum_views
import search.views as search_views

urlpatterns = [
    path('', forum_views.forums, name='forums-forums'),
    path('moderate/', forum_views.moderate_posts, name="forums-moderate"),
    path('forums-search/', search_views.search_forum, name="forums-search"),
    path('latest_posts/', forum_views.latest_posts, name="forums-latest-posts"),
    path('hot_treads/', forum_views.hot_threads, name="forums-hot-threads"),
    re_path(r'^(?P<forum_name_slug>[\w\-]+)/$', forum_views.forum, name="forums-forum"),
    re_path(r'^(?P<forum_name_slug>[\w\-]+)/new-thread/$', forum_views.new_thread, name="forums-new-thread"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', forum_views.thread, name="forums-thread"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/unsubscribe/$', forum_views.unsubscribe_from_thread, name="forums-thread-unsubscribe"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/subscribe/$', forum_views.subscribe_to_thread, name="forums-thread-subscribe"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', forum_views.post, name="forums-post"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/reply/$', forum_views.reply, name="forums-reply"),
    re_path(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/reply/$', forum_views.reply, name="forums-reply-quote"),

    path('post/<int:post_id>/edit/', forum_views.post_edit, name="forums-post-edit"),
    path('post/<int:post_id>/delete-confirm/', forum_views.post_delete_confirm, name="forums-post-delete-confirm"),
]
