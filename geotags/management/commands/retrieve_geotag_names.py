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

from django.db import transaction

from geotags.models import GeoTag
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):

    help = 'Retreive geotag names using the mapbox API for geotags that have no information'

    def add_arguments(self, parser):
        parser.add_argument(
            '-l', '--limit',
            action='store',
            dest='limit',
            default=5000,
            help='Maximum number of geotags to update')

    def handle(self, *args, **options):
        self.log_start()

        limit = int(options['limit'])
        geotags = GeoTag.objects.filter(should_update_information=True)[:limit]
        total = geotags.count()
        with transaction.atomic():
            for count, geotag in enumerate(geotags):
                geotag.retrieve_location_information()
                console_logger.info(f'Retrieved information for geotag {count + 1} of {total}')

        self.log_end({'num_geotags': total})
