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

from django.core.management.base import BaseCommand
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache

from sounds.models import Download

logger = logging.getLogger("web")


class Command(BaseCommand):
    help = "Create caches needed for front page"

    def handle(self, **options):
        logger.info("Updating front page caches")

        cache_time = 24 * 60 * 60  # 1 day cache time
        # NOTE: The specfic cache time not important as long as bigger than the frequency with which we run
        # create_front_page_caches management command

        # Generate cache for the blog news from blog's RSS feed
        # Create one for Freeesound Nightingale frontend and one for BeastWhoosh
        rss_cache = render_to_string('rss_cache.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache", rss_cache, cache_time)
        rss_cache_bw = render_to_string('molecules/news_cache.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache_bw", rss_cache_bw, cache_time)

        # TODO: we still don't know how to handle multiple news entries in BW, currently only the latest will be shown

        # Generate popular searches cache
        popular_searches = ['field-recording', 'ambience', 'voice', 'loop']
        cache.set("popular_searches", popular_searches,  cache_time)

        # TODO: we have to decide how do we determine "trending searches" and how often these are updated. Depending on
        # this we'll have to change the frequency with which we run create_front_page_caches management command

        # Generate trending sounds cache
        trending_sound_ids = list(Download.objects.order_by('-created').values_list('sound_id', flat=True)[0:3])
        cache.set("trending_sound_ids", trending_sound_ids,  cache_time)

        # TODO: decide how to compute trending sounds. Current implementation simply takes the 3 most recent downloads.
        # Depending on the calculation of trending sounds we might need to change periodicity with which we run
        # create_front_page_caches
