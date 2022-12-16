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

from builtins import range
import datetime

from django.conf import settings
from django.core.cache import cache

from sounds.models import SoundOfTheDay
from utils.management_commands import LoggingBaseCommand


class Command(LoggingBaseCommand):

    help = 'Add new SoundOfTheDay objects'

    def handle(self, *args, **options):
        self.log_start()

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
            for i in range(number_sounds):
                td = datetime.timedelta(days=i+1)
                SoundOfTheDay.objects.create_sound_for_date(datetime.date.today() + td)

        # Now delete existing cache of random sound so that it is reloaded the next time the sound is requested
        cache.delete(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY)

        self.log_end({'n_random_sounds_created': sounds_to_create})
