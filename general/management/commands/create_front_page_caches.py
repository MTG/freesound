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

import logging

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import Greatest
from django.template.loader import render_to_string
from django.core.cache import cache

from donations.models import Donation
from sounds.models import Download, Pack, Sound
from sounds.views import get_n_weeks_back_datetime
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")


class Command(LoggingBaseCommand):
    help = "Create caches needed for front page"

    def handle(self, **options):
        self.log_start()

        last_week = get_n_weeks_back_datetime(n_weeks=1)  # Use later to filter queries

        cache_time = 24 * 60 * 60  # 1 day cache time
        # NOTE: The specific cache time is not important as long as it is bigger than the frequency with which we run
        # create_front_page_caches management command

        # Generate cache for the blog news from blog's RSS feed
        # Create one for Freeesound Nightingale frontend and one for BeastWhoosh
        rss_cache = render_to_string('rss_cache.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache", rss_cache, cache_time)
        rss_cache_bw = render_to_string('molecules/news_cache.html', {'rss_url': settings.FREESOUND_RSS})
        if len(str(rss_cache_bw).strip()):
            cache.set("rss_cache_bw", rss_cache_bw, cache_time)
        else:
            cache.set("rss_cache_bw", None, cache_time)

        # Generate popular searches cache
        popular_searches = ['wind', 'music', 'footsteps', 'woosh', 'explosion', 'scream', 'click', 'whoosh', 'piano',
                            'swoosh', 'rain', 'fire']
        cache.set("popular_searches", popular_searches,  cache_time)

        # TODO: we have to decide how do we determine "trending searches" and how often these are updated. Depending on
        # this we'll have to change the frequency with which we run create_front_page_caches management command
        # Currently, this section is disabled in BW front page

        # Generate trending sounds cache (most downloaded sounds during last week)
        trending_sound_ids = Download.objects \
            .filter(created__gte=last_week).exclude(sound__is_explicit=True) \
            .values('sound_id').annotate(n_downloads=Count('sound_id')) \
            .order_by('-n_downloads').values_list('sound_id', flat=True)[0:9]
        cache.set("trending_sound_ids", list(trending_sound_ids),  cache_time)

        # Generate trending new sounds cache (most downloaded sounds from those created last week)
        trending_new_sound_ids = Sound.public.select_related('license', 'user') \
            .annotate(greatest_date=Greatest('created', 'moderation_date')) \
            .filter(greatest_date__gte=last_week).exclude(is_explicit=True) \
            .order_by("-num_downloads").values_list('id', flat=True)[0:9]
        cache.set("trending_new_sound_ids", list(trending_new_sound_ids),  cache_time)

        # Generate trending new packs cache (most downloaded packs from those created last week)
        trending_new_pack_ids = Pack.objects.select_related('user') \
            .filter(created__gte=last_week).exclude(is_deleted=True) \
            .order_by("-num_downloads").values_list('id', flat=True)[0:9]
        cache.set("trending_new_pack_ids", list(trending_new_pack_ids), cache_time)

        # Add total number of sounds in Freesound to the cache
        total_num_sounds = Sound.public.all().count()
        cache.set("total_num_sounds", total_num_sounds, cache_time)

        # Calculate top donor
        try:
            top_donor_user_data = Donation.objects \
                .filter(created__gt=last_week) \
                .exclude(user=None, is_anonymous=True) \
                .values('user_id').annotate(total_donations=Sum('amount')) \
                .order_by('-total_donations')[0]
            top_donor_user_id = top_donor_user_data['user_id']
            top_donor_donation_amount = '{:.2f} eur'.format(top_donor_user_data['total_donations'])
        except IndexError:
            top_donor_user_id = None
            top_donor_donation_amount = None
        cache.set("top_donor_user_id", top_donor_user_id, cache_time)
        cache.set("top_donor_donation_amount", top_donor_donation_amount, cache_time)

        self.log_end()
