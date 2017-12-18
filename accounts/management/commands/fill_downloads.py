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
from sounds.models import Download
from django.contrib.auth.models import User

logger = logging.getLogger("console")


class Command(BaseCommand):

    help = 'Copy number of Downloads to profiles'

    def handle(self, *args, **options):
        # This command will copy number of all the Downloads for each user
        logger.info('Copy number of Downloads started')

        td = datetime.timedelta(days=1)

        user_ids = Download.objects.order_by().values_list('user_id', flat=True).distinct()
        logger.info('Number of users to process: %d' % len(user_ids))

        for user_id in user_ids:
            u = User.objects.select_related('profile').prefetch_related('download_set').get(id=user_id)
            num_sound_downloads = 0
            num_pack_downloads = 0
            for download in u.download_set.all():
                if download.pack_id == None:
                    num_sound_downloads += 1
                else:
                    num_pack_downloads +=1

            u.profile.num_sound_downloads = num_sound_downloads
            u.profile.num_pack_downloads = num_pack_downloads
            u.profile.save()

        logger.info('Copy number of Downloads finished')
