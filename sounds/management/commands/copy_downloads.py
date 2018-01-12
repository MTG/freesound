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

import time
import datetime
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from sounds.models import Download, PackDownload, PackDownloadJson, PackDownloadSound
from django.db import transaction


logger = logging.getLogger("console")


class Command(BaseCommand):

    help = 'Copy Downloads to new models'
    def add_arguments(self, parser):
        parser.add_argument(
            '-s','--sleep',
            dest='sleep',
            default="0",
            help='Time in (seconds) to sleep after each day of Downlaods processed.')

    def handle(self, *args, **options):
        # This command will copy all the Downloads to the new models, it can be executed multiple
        # times and it will continue from the last period.
        logger.info('Copy Downloads to new PackDownload')

        sleep_time = int(options['sleep'])
        td = datetime.timedelta(days=1)

        # PackDownload disable created auto date

        PackDownload._meta.get_field('created').auto_now_add = False
        PackDownloadJson._meta.get_field('created').auto_now_add = False

        # get last date processed or if it's the first time executed use first date in downloads
        last_downloads = PackDownload.objects.order_by('-created')

        if last_downloads.count():
            start = last_downloads[0].created
            start = start.replace(hour=0, minute=0, second=0)
        else:
            first_downloads = Download.objects.order_by('created')
            start = first_downloads.first().created

        more_downloads = True
        while start < datetime.datetime.now():
            downloads = Download.objects.filter(pack_id__isnull=False, created__gte=start, created__lt=start+td)\
                    .prefetch_related('pack__sounds')
            start += td
            more_downloads = downloads.count() != 0
            with transaction.atomic():
                for download in downloads.all():
                    # create both PackDownload and PackDownloadJson
                    sounds = []
                    pd = PackDownload.objects.create(user=download.user, created=download.created, pack_id=download.pack_id)
                    pds = []
                    for sound in download.pack.sounds.all():
                        pds.append(PackDownloadSound(sound=sound, license=sound.license, pack_download=pd))
                        sounds.append({'sound_id': sound.id, 'license_id': sound.license_id})
                    PackDownloadSound.objects.bulk_create(pds, batch_size=1000)
                    PackDownloadJson.objects.create(user=download.user, created=download.created, pack_id=download.pack_id, sounds=sounds)

            logger.info("Copy of Download for %d packs of the date: %s " % (downloads.count(), start.strftime("%Y-%m-%d")))
            time.sleep(sleep_time)
        logger.info('Copy Downloads to new PackDownload finished')
