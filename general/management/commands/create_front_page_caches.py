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

from django.core.management.base import BaseCommand
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache
from django.db.models import Sum
import donations.models
import logging
logger = logging.getLogger("web")


class Command(BaseCommand):
    help = "Create front page RSS and Pledgie cache."

    def handle(self, **options):
        logger.info("Updating front page caches")

        rss_cache = render_to_string('rss_cache.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache", rss_cache, 2592000)  # 30 days cache

        campaign = donations.models.DonationCampaign.objects.order_by('date_start').last()
        all_donations = donations.models.Donation.objects\
                .filter(campaign=campaign).all().aggregate(Sum('amount'))
        if campaign:
            donations_goal = campaign.goal
            params = {'remains': int(donations_goal - (all_donations['amount__sum'] or 0)),
                      'percent_towards_goal': int((all_donations['amount__sum'] or 0) / donations_goal * 100)}
            donations_cache = render_to_string('donations_cache.html', params)
            cache.set("donations_cache", donations_cache, 2592000)  # 30 days cache
