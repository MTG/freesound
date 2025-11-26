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
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    raw_id_fields = ("sender", "assignee", "sound")
    list_display = ("id", "status", "assignee", "sender", "sound_link", "created")
    list_filter = ("status",)
    search_fields = (
        "=sender__username",
        "=sound__id",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("sender", "assignee", "sound")
        return qs

    def has_add_permission(self, request):
        return False

    @admin.display(
        description="Sound",
        ordering="sound_id",
    )
    def sound_link(self, obj):
        if obj.sound_id is None:
            return "-"
        return mark_safe(
            '<a href="{}" target="_blank">{}</a>'.format(reverse("short-sound-link", args=[obj.sound_id]), obj.sound)
        )
