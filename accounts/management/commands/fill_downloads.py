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
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger("console")


class Command(BaseCommand):

    help = 'Copy number of Downloads to profiles'

    def handle(self, *args, **options):
        # This command will copy number of all the Downloads for each user
        logger.info('Copy number of Downloads started')

        sql = """
        WITH sq as (select user_id, count(*) as num_downloads from sounds_download group by user_id)
        UPDATE accounts_profile set num_sound_downloads=sq.num_downloads
        FROM sq
        WHERE accounts_profile.user_id = sq.user_id;
        """

        with connection.cursor() as c:
            c.execute(sql)

        sql = """
        WITH sq as (select user_id, count(*) as num_downloads from sounds_packdownload group by user_id)
        UPDATE accounts_profile set num_pack_downloads=sq.num_downloads
        FROM sq
        WHERE accounts_profile.user_id = sq.user_id;
        """

        with connection.cursor() as c:
            c.execute(sql)

        logger.info('Copy number of Downloads finished')
