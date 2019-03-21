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
    help = "Create caches needed for front page"

    def handle(self, **options):
        logger.info("Updating front page caches")

        # Generate cache for the blog news from blog's RSS feed
        # Create one for Freeesound Nightingale frontend and one for BeastWhoosh
        rss_cache = render_to_string('rss_cache.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache", rss_cache, 2592000)  # 30 days cache
        rss_cache_bw = render_to_string('rss_cache_bw.html', {'rss_url': settings.FREESOUND_RSS})
        cache.set("rss_cache_bw", rss_cache_bw, 2592000)  # 30 days cache

        # TODO: we still don't know how to handle multiple news entries in BW, currently only the latest will be shown
