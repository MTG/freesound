from django import forms
from django.contrib import admin, messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django_object_actions import DjangoObjectActions, action

from .models import FeedbackExperiment, FeedbackOptOut, UserFeedback


class DownloadFeedbackForm(forms.Form):
    """Days of the feedback to download (both included). Empty means no limit."""

    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("experiment_id", "user", "country_iso_code", "created")
    list_filter = ("experiment_id", "created")
    search_fields = ("=user__username", "experiment_id")
    readonly_fields = ("experiment_id", "user", "country_iso_code", "data", "created")

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
    change_form_template = "user_feedback/admin_feedback_experiment_change_form.html"
    # Needed for the download URL, the button is replaced by the dates in the template
    change_actions = ("download_feedback",)

    @action(description="Download the feedback of this experiment as a JSON file", label="Download feedback")
    def download_feedback(self, request, obj):
        # The dates come from the fields in the experiment page; without dates, all the feedback is downloaded
        form = DownloadFeedbackForm(request.GET)
        if not form.is_valid():
            messages.error(request, "Invalid dates, please check them.")
            return redirect("admin:user_feedback_feedbackexperiment_change", obj.pk)
        feedback = UserFeedback.objects.filter(experiment_id=obj.experiment_id)
        filename = obj.experiment_id
        if form.cleaned_data["date_from"]:
            feedback = feedback.filter(created__date__gte=form.cleaned_data["date_from"])
            filename += f"_from_{form.cleaned_data['date_from']}"
        if form.cleaned_data["date_to"]:
            feedback = feedback.filter(created__date__lte=form.cleaned_data["date_to"])
            filename += f"_to_{form.cleaned_data['date_to']}"
        # One item per UserFeedback, with all its fields
        fields = ("id", "experiment_id", "user_id", "country_iso_code", "data", "created")
        rows = list(feedback.order_by("created").values(*fields))
        response = JsonResponse(rows, safe=False, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f'attachment; filename="{filename}_feedback.json"'
        return response

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
