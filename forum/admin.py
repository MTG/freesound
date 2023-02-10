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

from django.contrib import admin
from forum.models import Forum, Thread, Post

@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    raw_id_fields = ('last_post', )
    list_display = ('name', 'num_threads', 'change_order')



@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'last_post','first_post' )
    list_display = ('forum', 'author', 'title', 'status', 'num_posts', 'created')
    list_filters = ('status',)
    search_fields = ('=author__username', "title")



@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'thread')
    list_display = ('thread', 'author', 'created')
    search_fields = ('=author__username', "body")

