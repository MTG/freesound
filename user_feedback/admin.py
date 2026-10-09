from django.contrib import admin
from django.http import JsonResponse
from django_object_actions import DjangoObjectActions, action

from .models import FeedbackExperiment, FeedbackOptOut, UserFeedback


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("experiment_id", "user", "ip", "created")
    list_filter = ("experiment_id", "created")
    search_fields = ("=user__username", "experiment_id")
    readonly_fields = ("experiment_id", "user", "ip", "data", "created")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FeedbackOptOut)
class FeedbackOptOutAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("user", "experiment_id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FeedbackExperiment)
class FeedbackExperimentAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = ("experiment_id", "sample_rate", "title")
    readonly_fields = ("experiment_id",)
    change_actions = ("download_feedback",)

    @action(description="Download all the feedback of this experiment as a JSON file", label="Download feedback")
    def download_feedback(self, request, obj):
        # One item per UserFeedback of the experiment, with all its fields
        feedback = UserFeedback.objects.filter(experiment_id=obj.experiment_id).order_by("created")
        rows = list(feedback.values("id", "experiment_id", "user_id", "ip", "data", "created"))
        response = JsonResponse(rows, safe=False, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{obj.experiment_id}_feedback.json"'
        return response

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
