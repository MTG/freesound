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
from sounds.models import Sound, SoundOfTheDay

logger = logging.getLogger("gearman_worker_processing")


class Command(BaseCommand):

    help = 'Add new SoundOfTheDay objects'

    def create_random_sound(self, date_display):
        # Generate a list of users to exclude
        days_for_user = settings.NUMBER_OF_DAYS_FOR_USER_RANDOM_SOUNDS
        date_from = date_display - datetime.timedelta(days=days_for_user)
        users = SoundOfTheDay.objects.filter(
                date_display__lt=date_display,
                date_display__gte=date_from).values_list('sound__user_id', flat=True)
        used_sounds = SoundOfTheDay.objects.values_list('sound_id', flat=True)

        already_created = SoundOfTheDay.objects.filter(date_display=date_display).count()
        while not already_created:
            # Get random sound and check if the user is not excluded
            sound = Sound.objects.random()
            if not sound.user_id in list(users) and sound.id not in used_sounds:
                rnd = SoundOfTheDay.objects.create(sound=sound, date_display=date_display)
                logger.info("Created new Random Sounds with id %d" % rnd.id)
                already_created = True

    def handle(self, *args, **options):
        logger.info('Create new RandomSound task')

        # First make sure there is a sound for today
        self.create_random_sound(datetime.date.today())

        # Then create sounds in advance
        number_sounds = settings.NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE
        already_created = SoundOfTheDay.objects.filter(date_display__gt=datetime.date.today()).count()
        sounds_to_create = number_sounds - already_created
        if sounds_to_create > 0:
            logger.info("Creating %d new Random Sounds" % sounds_to_create)
            for i in range(number_sounds):
                td = datetime.timedelta(days=i+1)
                self.create_random_sound(datetime.date.today()+td)
        logger.info('Create new RandomSound task ended')


