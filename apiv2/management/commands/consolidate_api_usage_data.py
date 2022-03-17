# -*- coding: utf-8 -*-

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
import logging

from django.core.cache import caches

from utils.management_commands import LoggingBaseCommand
from apiv2.models import ApiV2Client, APIClientDailyUsageHistory


console_logger = logging.getLogger("console")
cache_api_monitoring = caches["api_monitoring"]


class Command(LoggingBaseCommand):

    help = 'Consolidate API usage data stored in cache backend to the database. This command will look for entries in' \
           ' the cache which correspond to stored "requests per client" counts for the last 2 days. It will update ' \
           'corresponding APIClientDailyUsageHistory objects in the database so the information is saved permanently' \
           'before the cache items expire.'

    def handle(self, *args, **options):
        self.log_start()

        n_days_back = 2
        now = datetime.datetime.now().date()
        for i in range(0, n_days_back):
            date_filter = now - datetime.timedelta(days=i)
            monitoring_key_pattern = '{0}-{1}-{2}_*'.format(date_filter.year, date_filter.month, date_filter.day)
            for key, count in cache_api_monitoring.get_many(cache_api_monitoring.keys(monitoring_key_pattern)).items():
                try:
                    apiv2_client = ApiV2Client.objects.get(oauth_client__client_id=key.split('_')[1])
                    usage_history, _ = APIClientDailyUsageHistory\
                        .objects.get_or_create(date=date_filter, apiv2_client=apiv2_client)
                    usage_history.number_of_requests = count
                    usage_history.save()
                except ApiV2Client.DoesNotExist:
                    # Client has been deleted, no usage history to update
                    pass

        self.log_end()
