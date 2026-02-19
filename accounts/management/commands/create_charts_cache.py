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
from django.core.cache import caches

from accounts.views import compute_charts_stats
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
cache_persistent = caches["persistent"]


class Command(LoggingBaseCommand):
    help = "Create caches needed for the charts page"

    def handle(self, **options):
        self.log_start()
        tvars = compute_charts_stats()
        cache_persistent.set(settings.CHARTS_DATA_CACHE_KEY, tvars, 60 * 60 * 24)
        self.log_end()
