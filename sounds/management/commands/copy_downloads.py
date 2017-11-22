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
from sounds.models import Download, PackDownload, PackDownloadJson, PackDownloadSound

logger = logging.getLogger("console")


class Command(BaseCommand):

    help = 'Copy Downloads to new models'

    def handle(self, *args, **options):
        # This command will copy all the Downloads to the new models, it can be executed multiple
        # times and it will continue from the last period.
        logger.info('Copy Downloads to new PackDownload')

        td = datetime.timedelta(days=1)

        # PackDownload disable created auto date

        PackDownload._meta.get_field('created').auto_now_add = False
        PackDownloadJson._meta.get_field('created').auto_now_add = False

        # get last date processed or if it's the first time executed use first date in downloads
        last_downloads = PackDownload.objects.order_by('-created')

        if last_downloads.count():
            start = last_downloads[0].created
            start = start.replace(hour=0, minute=0, second=0)
            PackDownload.objects.filter(created__gt=start).delete()
            PackDownloadJson.objects.filter(created__gt=start).delete()
        else:
            first_downloads = Download.objects.order_by('created')
            start = first_downloads.first().created

        more_downloads = True
        while start < datetime.datetime.now():
            downloads = Download.objects.filter(pack_id__isnull=False, created__gte=start, created__lt=start+td)
            start += td
            more_downloads = downloads.count() != 0
            for download in downloads.all():
                # create both PackDownload and PackDownloadJson

                sounds = []
                pd = PackDownload.objects.create(user=download.user, created=download.created, pack_id=download.pack_id)
                for sound in download.pack.sound_set.all():
                    PackDownloadSound.objects.create(sound=sound, license=sound.license, pack_download=pd)
                    sounds.append({'sound_id': sound.id, 'license_id': sound.license_id})
                PackDownloadJson.objects.create(user=download.user, created=download.created, pack_id=download.pack_id, sounds=sounds)

            logger.info("Copy of Download for %d sounds of the date: %s " % (downloads.count(), start.strftime("%Y-%m-%d")))
        logger.info('Copy Downloads to new PackDownload finished')
