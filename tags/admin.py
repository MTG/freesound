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
from tags.models import Tag, TaggedItem

class TagAdmin(admin.ModelAdmin):
    list_display = ('tag',)

admin.site.register(Tag)

@admin.register(TaggedItem)
class TaggedItemAdmin(admin.ModelAdmin):
    search_fields = ('=tag__name',)
    raw_id_fields = ('user', 'tag')
    list_display = ('user', 'content_type', 'object_id', 'tag', 'created')

