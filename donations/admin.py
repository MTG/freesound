from urllib.parse import urlencode

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
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
        url = reverse("admin:donations_donationrequest_changelist")
        params = urlencode({"q": obj.user.username})
        return HttpResponseRedirect(f"{url}?{params}")
