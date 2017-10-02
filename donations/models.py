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

    DONATION_CHOICES =(
        ('p', 'paypal'),
        ('s', 'stripe'),
        ('t', 'transfer'),
    )
    source = models.CharField(max_length=2, choices=DONATION_CHOICES, default='p')


class DonationsModalSettings(models.Model):
    enabled = models.BooleanField(default=False)
    never_show_modal_to_uploaders = models.BooleanField(default=True)
    days_after_donation = models.PositiveIntegerField(
        default=365, help_text='If user made a donation in the last X days, no modal is shown')
    downloads_in_period = models.PositiveIntegerField(default=5, help_text='After user has download Z sounds...')
    download_days = models.PositiveIntegerField(default=7, help_text='...in Y days, we display the modal')
    display_probability = models.FloatField(
        default=0.25, help_text='probabily of the modal being shown once all previous requirements are met')
    max_times_display_a_day = models.PositiveIntegerField(
        default=10, help_text='max number of times we display the modal during a single day')

    DONATION_MODAL_SETTINGS_CACHE_KEY = 'donation-modal-settings'

    @classmethod
    def get_donation_modal_settings(cls):
        """
        Return the current setting stored in the model.
        Because this model will be queryied often (every time a user downloads a sound), we want to avoid hitting the
        DB every time. We store the settings in the cache and return the data from there (if exists).
        """
        instance = cache.get(cls.DONATION_MODAL_SETTINGS_CACHE_KEY, None)
        if instance is None:
            instance, _ = cls.objects.get_or_create()  # Gets existing object or creates it
            cache.set(cls.DONATION_MODAL_SETTINGS_CACHE_KEY, instance, timeout=3600)
        return instance


class DonationsEmailSettings(models.Model):
    enabled = models.BooleanField(default=False)
    never_send_email_to_uploaders = models.BooleanField(default=True)
    minimum_days_since_last_donation = models.PositiveIntegerField(
        default=365, help_text="Send emails to user only if didn't made a donation in the last X days")
    minimum_days_since_last_donation_email = models.PositiveIntegerField(
        default=30*3, help_text="Don't send a donation email if the last one was sent in less than X days")
    downloads_in_period = models.PositiveIntegerField(default=100, help_text='After user has download Z sounds...')

