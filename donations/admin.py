from urllib.parse import urlencode

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from .models import (
    Donation,
    DonationCampaign,
    DonationRequest,
    DonationsEmailSettings,
    DonationsModalSettings,
)

admin.site.register(DonationCampaign)


@admin.register(DonationsModalSettings)
class DonationsModalSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        num_objects = self.model.objects.count()
        if num_objects >= 1:
            return False
        else:
            return True


@admin.register(DonationsEmailSettings)
class DonationsEmailSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        num_objects = self.model.objects.count()
        if num_objects >= 1:
            return False
        else:
            return True


@admin.register(DonationRequest)
class DonationRequestAdmin(DjangoObjectActions, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ("request_type", "user", "created")
    list_filter = ("request_type",)
    readonly_fields = ("user", "request_type", "created")
    search_fields = ("=user__username",)
    change_actions = ("view_donations_for_user",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("user")
        return qs

    @admin.action(description="View donations by this user")
    def view_donations_for_user(self, request, obj):
        url = reverse("admin:donations_donation_changelist")
        params = urlencode({"q": obj.user.username})
        return HttpResponseRedirect(f"{url}?{params}")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Donation)
class DonationAdmin(DjangoObjectActions, admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = (
        "id",
        "email",
        "user",
        "amount",
        "currency",
        "created",
    )
    search_fields = (
        "=user__username",
        "=email",
    )
    change_actions = ("view_donations_requests_for_user",)
    readonly_fields = (
        "get_donation_requests_before_donation",
        "get_previous_donations",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("user")
        return qs

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="View donation requests for this user")
    def view_donations_requests_for_user(self, request, obj):
        if obj.user is None:
            self.message_user(request, "This donation has no associated user account.", level=messages.WARNING)
            return None
        url = reverse("admin:donations_donationrequest_changelist")
        params = urlencode({"q": obj.user.username})
        return HttpResponseRedirect(f"{url}?{params}")

    @admin.display(description="Donation Requests before donation")
    def get_donation_requests_before_donation(self, obj):
        donation_requests = obj.get_donation_requests_before_donation()
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(dr.created.date(), dr.get_request_type_display())
            for dr in donation_requests
        )
        return mark_safe(f"<table>{rows}</table>")

    @admin.display(description="Previous donations by same user")
    def get_previous_donations(self, obj):
        previous_donations = obj.get_previous_donations(only_last=False)
        rows = "".join(
            "<tr><td>{}</td><td>{}</td></tr>".format(pd.created.date(), f"{pd.amount} {pd.currency}")
            for pd in previous_donations
        )
        return mark_safe(f"<table>{rows}</table>")
