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
from django.conf import settings
from django.utils import timezone
import os
import datetime


class Command(BaseCommand):
    help = "Cleans all files in FILE_UPLOAD_TEMP_DIR which are older than 24 hours"

    def handle(self, *args, **options):
        for f in os.listdir(settings.FILE_UPLOAD_TEMP_DIR):
            f_mod_date = datetime.datetime.fromtimestamp(
                os.path.getmtime(settings.FILE_UPLOAD_TEMP_DIR + f), tz=datetime.timezone.utc
            )
            now = timezone.now()
            if (now - f_mod_date).total_seconds() > 3600 * 24:
                print(f"Deleting {f}")
                os.remove(settings.FILE_UPLOAD_TEMP_DIR + f)
