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

from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache

class Command(NoArgsCommand):
    help = "Create front page RSS and Pledgie cache."

    def handle(self, **options):
        rss_url = settings.FREESOUND_RSS
        pledgie_campaign = settings.PLEDGIE_CAMPAIGN
        
        rss_cache = render_to_string('rss_cache.html', locals())
        cache.set("rss_cache", rss_cache, 2592000) # 30 days cache

        pledgie_cache = render_to_string('pledgie_cache.html', locals())
        cache.set("pledgie_cache", pledgie_cache, 2592000) # 30 days cache