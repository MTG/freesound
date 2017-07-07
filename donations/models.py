from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.core.cache import cache


class DonationCampaign(models.Model):
    goal = models.DecimalField(max_digits=6, decimal_places=2)
    date_start = models.DateField()


class Donation(models.Model):
    user = models.ForeignKey(User, null=True, blank=True)
    email = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, null=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=100) # Should always be EUR
    created = models.DateTimeField(auto_now_add=True)
    campaign = models.ForeignKey(DonationCampaign, null=True)
    is_anonymous= models.BooleanField(default=True)
    display_amount = models.BooleanField(default=True)


class DonationsModalSettings(models.Model):
    enabled = models.BooleanField(default=False)
    days_after_donation = models.PositiveIntegerField(
        default=365, help_text='If user made a donation in the last X days, no modal is shown')
    downloads_in_period = models.PositiveIntegerField(default=5, help_text='After user has download Z sounds...')
    download_days = models.PositiveIntegerField(default=7, help_text='...in Y days, we display the modal')
    display_probability = models.FloatField(
        default=0.25, help_text='probabily of the modal being shown once all previous requirements are met')
    max_times_display_a_day = models.PositiveIntegerField(
        default=10, help_text='max number of times we display the modal during a single day')

    DONATION_MODAL_SETTINGS_CACHE_KEY = 'donation-modal-settings'

    def get_donation_modal_settings(self):
        """
        Return the current setting stored in the model.
        Because this model will be queryied often (every time a user downloads a sound), we want to avoid hitting the
        DB every time. We store the settings in the cache and return the data from there (if exists).
        """
        settings = cache.get(self.DONATION_MODAL_SETTINGS_CACHE_KEY, None)
        if settings is None:
            settings = {
                'enabled': self.enabled,
                'days_after_donation': self.days_after_donation,
                'downloads_in_period': self.downloads_in_period,
                'download_days': self.download_days,
                'max_times_display_a_day': self.max_times_display_a_day,
            }
            cache.set(self.DONATION_MODAL_SETTINGS_CACHE_KEY, settings, timeout=3600)
        return settings
