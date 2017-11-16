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
from sounds.models import SoundOfTheDay

logger = logging.getLogger("console")


class Command(BaseCommand):

    help = 'Add new SoundOfTheDay objects'

    def handle(self, *args, **options):
        logger.info('Create new RandomSound task')

        # First make sure there is a sound for today
        today = datetime.date.today()
        SoundOfTheDay.objects.create_sound_for_date(today)
        sound = SoundOfTheDay.objects.get_sound_for_date(today)
        sound.notify_by_email()

        # Then create sounds in advance
        number_sounds = settings.NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE
        already_created = SoundOfTheDay.objects.filter(date_display__gt=datetime.date.today()).count()
        sounds_to_create = number_sounds - already_created
        if sounds_to_create > 0:
            logger.info("Creating %d new Random Sounds" % sounds_to_create)
            for i in range(number_sounds):
                td = datetime.timedelta(days=i+1)
                SoundOfTheDay.objects.create_sound_for_date(datetime.date.today() + td)
                logger.info('Created new Random Sound')
        logger.info('Create new RandomSound task ended')
