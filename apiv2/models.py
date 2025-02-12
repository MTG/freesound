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

import datetime
import random

from django.db import models
from django.contrib.auth.models import User
from oauth2_provider.models import Application
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.sites.models import Site


class ApiV2Client(models.Model):

    STATUS_CHOICES = (('OK',  'Approved'),
                      ('REJ', 'Rejected'),
                      ('REV', 'Revoked'),
                      ('PEN', 'Pending'))

    DEFAULT_STATUS = 'OK'

    oauth_client = models.OneToOneField(
        Application, related_name='apiv2_client', default=None, null=True, blank=True, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, blank=True)
    user = models.ForeignKey(User, related_name='apiv2_client', on_delete=models.CASCADE)
    status = models.CharField(max_length=3, default=DEFAULT_STATUS, choices=STATUS_CHOICES)
    name = models.CharField(max_length=64)
    url = models.URLField(blank=True)
    redirect_uri = models.URLField()
    description = models.TextField(blank=True)
    accepted_tos = models.BooleanField(default=False)
    allow_oauth_passoword_grant = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    throttling_level = models.IntegerField(default=1)

    def __str__(self):
        return f"credentials for developer {self.user.username}"

    def save(self, *args, **kwargs):

        # If oauth client does not exist create a new one (that means ApiV2Client is being saved for the first time)
        # Otherwise update existing client

        # If redirect_uri has not been set, use Freesound redirect uri by default
        if not self.redirect_uri:
            self.redirect_uri = self.get_default_redirect_uri()

        if not self.oauth_client:
            # Set oauth client (create oauth client object)
            oauth_client = Application(
                user=self.user,
                name=self.name,
                redirect_uris=self.redirect_uri,
                client_type=Application.CLIENT_PUBLIC,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
            )
            # Save un-hashed client secret as "key" so we can show it to developers
            self.key = oauth_client.client_secret

            # Now save the Application object (note that once saved, the .client_secret is hashed, that is why we
            # need to assign self.key before saving).
            oauth_client.save()

            # Assign oauth client to our ApiV2Client model
            self.oauth_client = oauth_client

        else:
            # Update existing oauth client
            self.oauth_client.name = self.name
            self.oauth_client.redirect_uris = self.redirect_uri
            self.oauth_client.save()

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # On delete, delete also oauth client
        self.oauth_client.delete()
        super().delete(*args, **kwargs)

    def get_usage_history(self, n_days_back=30, year=None):
        """Returns the total number of daily requests made per day for the current API client during the last 
        N days or during the indicated year. The result is a list of tuples with the date and the count, 
        sorted by date (older first).

        Args:
            n_days_back (int): number of days for which to get the requests count
            year (int): year in which the requests were made (if set, n_days_back is ignored)

        Returns:
            List[Tuple(datetime.Date, int)]
        """
        usage = []
        if year is not None:
            end_date = datetime.datetime(year, 12, 31).date()
            n_days_back = 365
        else:
            end_date = timezone.now().date()
        for i in range(0, n_days_back):
            date_filter = end_date - datetime.timedelta(days=i)
            if settings.DEBUG:
                number_of_requests = random.randint(0, 1000)
            else:
                try:
                    number_of_requests = self.usage.get(date=date_filter).number_of_requests
                except APIClientDailyUsageHistory.DoesNotExist:
                    number_of_requests = 0    
            usage.append((date_filter, number_of_requests))
        return sorted(usage, reverse=True)

    def get_usage_history_total(self, n_days_back=30, year=None, discard_per_day=0):
        """Returns the total number of API requests carried out by the API client in the last
        n_days_back or in the specified year (see self.get_usage_history for more details). 
        Additionally, a number of "discard_per_day" requests can set to ignore that amount of
        daily requests when computing the total.
        """
        return sum([max(u - discard_per_day, 0) for _, u in self.get_usage_history(n_days_back=n_days_back, year=year)])

    def get_default_redirect_uri(self):
        return f"http{'s' if not settings.DEBUG else ''}://" \
               f"{Site.objects.get_current().domain}{reverse('permission-granted')}"

    @property
    def client_id(self):
        return self.oauth_client.client_id

    @property
    def client_secret(self):
        return self.key  # We can't use self.oauth_client.client_secret as it is hashed
    
    @property
    def version(self):
        return "V2"


class APIClientDailyUsageHistory(models.Model):
    apiv2_client = models.ForeignKey(ApiV2Client, related_name='usage', on_delete=models.CASCADE)
    number_of_requests = models.PositiveIntegerField(default=0)
    date = models.DateField()

    class Meta:
        ordering = ("-date",)
        unique_together = ('apiv2_client', 'date')
