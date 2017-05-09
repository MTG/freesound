from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models

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
