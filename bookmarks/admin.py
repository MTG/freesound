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
from bookmarks.models import Bookmark, BookmarkCategory

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    raw_id_fields = ('user','category','sound') 
    list_display = ('user', 'name', 'category', 'sound')

@admin.register(BookmarkCategory)
class BookmarkCategoryAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'name')


