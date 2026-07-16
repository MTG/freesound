from django.contrib import admin

from .models import UserFeedback


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("experiment_id", "user", "ip", "created")
    list_filter = ("experiment_id", "created")
    search_fields = ("=user__username", "experiment_id")
    readonly_fields = ("experiment_id", "user", "ip", "data", "created")

    # Feedback is collected from users -- treat the admin as a read-only log.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
