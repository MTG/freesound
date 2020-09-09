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

import os

from django.db.models.signals import post_syncdb
from django.dispatch import receiver
from django.conf import settings

from utils.filesystem import create_directories


@receiver(post_syncdb)
def create_locations(sender, **kwargs):
    for folder in [settings.SOUNDS_PATH,
                   settings.PACKS_PATH,
                   settings.AVATARS_PATH,
                   settings.UPLOADS_PATH,
                   settings.PREVIEWS_PATH,
                   settings.DISPLAYS_PATH,
                   settings.FILE_UPLOAD_TEMP_DIR]:
        if not os.path.isdir(folder):
            create_directories(folder, exist_ok=True)
        else:
            print ("Folder: '%s' already exists" % folder)
