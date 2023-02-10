from django.contrib import admin
from .models import DonationCampaign, DonationsModalSettings, DonationsEmailSettings, Donation

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


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)

    def has_change_permission(self, request, obj=None):
        return False


