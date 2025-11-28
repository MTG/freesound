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
import random

from django.conf import settings
from django.core.cache import caches
from django.db.models import Count, Sum
from django.db.models.functions import Greatest
from django.template.loader import render_to_string
from django.utils import timezone

from donations.models import Donation
from sounds.models import Download, Pack, Sound, SoundOfTheDay
from sounds.views import get_n_weeks_back_datetime
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
cache_persistent = caches["persistent"]


class Command(LoggingBaseCommand):
    help = "Create caches needed for front page"

    def handle(self, **options):
        self.log_start()

        NUM_ITEMS_PER_SECTION = 9

        last_week = get_n_weeks_back_datetime(n_weeks=1)  # Use later to filter queries
        last_two_weeks = get_n_weeks_back_datetime(n_weeks=2)  # Use later to filter queries

        cache_time = 24 * 60 * 60  # 1 day cache time
        # NOTE: The specific cache time is not important as long as it is bigger than the frequency with which we run
        # create_front_page_caches management command

        # Generate cache for the blog news from blog's RSS feed
        # Create one for Freeesound Nightingale frontend and one for BeastWhoosh
        rss_cache_bw = render_to_string("molecules/news_cache.html", {"rss_url": settings.FREESOUND_RSS})
        if len(rss_cache_bw.strip()):
            cache_persistent.set("rss_cache", rss_cache_bw, cache_time)
        else:
            cache_persistent.set("rss_cache", None, cache_time)

        # Generate popular searches cache
        # TODO: implement this properly if we want to add this functionality
        popular_searches = [
            "wind",
            "music",
            "footsteps",
            "woosh",
            "explosion",
            "scream",
            "click",
            "whoosh",
            "piano",
            "swoosh",
            "rain",
            "fire",
        ]
        cache_persistent.set("popular_searches", popular_searches, cache_time)

        # Generate trending sounds cache (most downloaded sounds during last week)
        trending_sound_ids = (
            Download.objects.filter(created__gte=last_week)
            .exclude(sound__is_explicit=True)
            .values("sound_id")
            .annotate(n_downloads=Count("sound_id"))
            .order_by("-n_downloads")
            .values_list("sound_id", flat=True)[0 : NUM_ITEMS_PER_SECTION * 5]
        )
        trending_sound_ids = list(trending_sound_ids)
        random.shuffle(trending_sound_ids)  # Randomize the order of the sounds
        cache_persistent.set("trending_sound_ids", trending_sound_ids[0:NUM_ITEMS_PER_SECTION], cache_time)

        # Generate trending new sounds cache (most downloaded sounds from those created last week)
        trending_new_sound_ids = (
            Sound.public.select_related("license", "user")
            .annotate(greatest_date=Greatest("created", "moderation_date"))
            .filter(greatest_date__gte=last_week)
            .exclude(is_explicit=True)
            .order_by("-num_downloads")
            .values_list("id", flat=True)[0 : NUM_ITEMS_PER_SECTION * 5]
        )
        trending_new_sound_ids = list(trending_new_sound_ids)
        random.shuffle(trending_new_sound_ids)  # Randomize the order of the sounds
        cache_persistent.set("trending_new_sound_ids", trending_new_sound_ids[0:NUM_ITEMS_PER_SECTION], cache_time)

        # Generate trending new packs cache (most downloaded packs from those created last week)
        trending_new_pack_ids = (
            Pack.objects.select_related("user")
            .filter(created__gte=last_week, num_sounds__gt=0)
            .exclude(is_deleted=True)
            .order_by("-num_downloads")
            .values_list("id", flat=True)[0 : NUM_ITEMS_PER_SECTION * 5]
        )
        trending_new_pack_ids = list(trending_new_pack_ids)
        random.shuffle(trending_new_pack_ids)  # Randomize the order of the packs
        cache_persistent.set("trending_new_pack_ids", trending_new_pack_ids[0:NUM_ITEMS_PER_SECTION], cache_time)

        # Generate top rated new sounds cache (top rated sounds from those created last two weeks)
        # Note we use two weeks here instead of one to make sure we have enough sounds to choose from
        top_rated_new_sound_ids = (
            Sound.public.select_related("license", "user")
            .annotate(greatest_date=Greatest("created", "moderation_date"))
            .filter(greatest_date__gte=last_two_weeks)
            .exclude(is_explicit=True)
            .filter(num_ratings__gt=settings.MIN_NUMBER_RATINGS)
            .order_by("-avg_rating", "-num_ratings")
            .values_list("id", flat=True)[0 : NUM_ITEMS_PER_SECTION * 5]
        )
        top_rated_new_sound_ids = list(top_rated_new_sound_ids)
        random.shuffle(top_rated_new_sound_ids)  # Randomize the order of the sounds
        cache_persistent.set("top_rated_new_sound_ids", top_rated_new_sound_ids[0:NUM_ITEMS_PER_SECTION], cache_time)

        # Generate latest "random sound of the day" ids
        recent_random_sound_ids = [
            sd.sound_id
            for sd in SoundOfTheDay.objects.filter(date_display__lt=timezone.now()).order_by("-date_display")[
                :NUM_ITEMS_PER_SECTION
            ]
        ]
        cache_persistent.set("recent_random_sound_ids", list(recent_random_sound_ids), cache_time)

        # Add total number of sounds in Freesound to the cache
        total_num_sounds = Sound.public.all().count()
        cache_persistent.set("total_num_sounds", total_num_sounds, cache_time)

        # Calculate top donor
        try:
            top_donor_user_data = (
                Donation.objects.filter(created__gt=last_week)
                .exclude(user=None, is_anonymous=True)
                .values("user_id")
                .annotate(total_donations=Sum("amount"))
                .order_by("-total_donations")[0]
            )
            top_donor_user_id = top_donor_user_data["user_id"]
            top_donor_donation_amount = f"{top_donor_user_data['total_donations']:.2f} eur"
        except IndexError:
            top_donor_user_id = None
            top_donor_donation_amount = None
        cache_persistent.set("top_donor_user_id", top_donor_user_id, cache_time)
        cache_persistent.set("top_donor_donation_amount", top_donor_donation_amount, cache_time)

        self.log_end()
