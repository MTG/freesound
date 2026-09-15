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

from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from apiv2.models import ApiV2Client


def make_set_throttling_level_action(level):
    def set_throttling_level(modeladmin, request, queryset):
        queryset.update(throttling_level=level)

    set_throttling_level.__name__ = f"set_throttling_level_{level}"
    set_throttling_level.short_description = f"Set throttling level to {level}"
    return set_throttling_level


@admin.register(ApiV2Client)
class ApiV2ClientAdmin(admin.ModelAdmin):
    raw_id_fields = ("user", "oauth_client")
    readonly_fields = ("created", "get_last_7_days_usage")
    search_fields = ("=user__username", "name", "=oauth_client__client_id", "=key", "description")
    list_filter = ("status", "throttling_level")
    list_display = ("name", "url", "get_user_link", "status", "throttling_level", "get_today_usage", "created")
    actions = [make_set_throttling_level_action(level) for level in settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS]

    def has_add_permission(self, request):
        return False

    @admin.display(description="User", ordering="user__username")
    def get_user_link(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(reverse("admin:auth_user_change", args=[obj.user_id]), obj.user.username)
        )

    @admin.display(description="Requests today")
    def get_today_usage(self, obj):
        return obj.get_current_today_usage_from_cache()

    @admin.display(description="Requests per day in the last 7 days")
    def get_last_7_days_usage(self, obj):
        usage = obj.get_usage_history(n_days_back=7)
        today = timezone.now().date()
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(
                date, obj.get_current_today_usage_from_cache() if date == today else count
            )
            for date, count in usage
        )
        return mark_safe(f"<table>{rows}</table>")
