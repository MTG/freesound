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

from comments.models import Comment
from utils.admin_helpers import NoPkDescOrderedChangeList


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    fieldsets = ((None, {'fields': ('user', 'sound', 'comment')}),)
    raw_id_fields = ('user', 'parent', 'sound')
    list_display = ('user', 'created', 'get_comment_summary', 'sound')
    list_select_related = ('user', 'sound')
    list_filter = ('contains_hyperlink',)
    search_fields = ('comment', '=user__username', '=sound__id')
    ordering = ('-created',)

    @admin.display(description='Comment')
    def get_comment_summary(self, obj):
        max_len = 80
        return f"{obj.comment[:max_len]}{'...' if len(obj.comment) > max_len else ''}"

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_changelist(self, request):
        # Use custom change list class to avoid ordering by '-pk' in addition to '-created'
        # That would cause a slow query as we don't have a combined db index on both fields
        return NoPkDescOrderedChangeList
