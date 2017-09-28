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
from django.db import connection
import logging

logger = logging.getLogger("web")

class Command(BaseCommand):

    help = 'Update Downloads license from sound table'

    def add_arguments(self, parser):
        parser.add_argument('limit', type=int, nargs='?', default=10000, help='Limit of Download rows to update at each step')

    def handle(self, *args, **options):
        limit = options['limit']
        logger.info("Starting to update Download licenses")

        more_results = True
        while more_results:
            more_results = False
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH sub AS 
                        (SELECT id 
                           FROM sounds_download 
                          WHERE license_id is null AND sound_id is not null
                       ORDER BY id 
                          LIMIT %s 
                     FOR UPDATE SKIP LOCKED ) 
                  UPDATE sounds_download sd 
                     SET license_id=s.license_id 
                    FROM sub 
                       , sounds_sound s 
                   WHERE sub.id = sd.id 
                     AND s.id=sd.sound_id
                    """, (limit,))
                more_results = cursor.rowcount
                logger.info("Updated %i Download licenses" % (more_results))
        logger.info("Finished updating Download licenses")

