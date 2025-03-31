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
from messages.models import Message, MessageBody

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ['user_from', 'user_to', 'body']
    list_display = ['user_from', 'user_to', 'subject', 'is_sent', 'is_read', 'is_archived', 'created']
    search_fields = ['=user_from__username', '=user_to__username', 'subject']
    list_filter = ['is_sent', 'is_read', 'is_archived']
    readonly_fields = ['message_body']

    def message_body(self, obj):
        return obj.body.body


admin.site.register(MessageBody)
