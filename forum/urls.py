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
import forum.views as forum_views
import search.views as search_views

urlpatterns = [
    url(r'^$', forum_views.forums, name='forums-forums'),
    url(r'^moderate/$', forum_views.moderate_posts, name="forums-moderate"),
    url(r'^forums-search/$', search_views.search_forum, name="forums-search"),
    url(r'^latest_posts/$', forum_views.latest_posts, name="forums-latest-posts"),
    url(r'^hot_treads/$', forum_views.hot_threads, name="forums-hot-threads"),
    url(r'^(?P<forum_name_slug>[\w\-]+)/$', forum_views.forum, name="forums-forum"),
    url(r'^(?P<forum_name_slug>[\w\-]+)/new-thread/$', forum_views.new_thread, name="forums-new-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', forum_views.thread, name="forums-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/unsubscribe/$', forum_views.unsubscribe_from_thread, name="forums-thread-unsubscribe"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/subscribe/$', forum_views.subscribe_to_thread, name="forums-thread-subscribe"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', forum_views.post, name="forums-post"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/reply/$', forum_views.reply, name="forums-reply"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/reply/$', forum_views.reply, name="forums-reply-quote"),

    url(r'^post/(?P<post_id>\d+)/edit/$', forum_views.post_edit, name="forums-post-edit"),
    url(r'^post/(?P<post_id>\d+)/delete/$', forum_views.post_delete, name="forums-post-delete"),
    url(r'^post/(?P<post_id>\d+)/delete-confirm/$', forum_views.post_delete_confirm, name="forums-post-delete-confirm"),
]
