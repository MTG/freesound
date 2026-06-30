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
import os
import subprocess

from django.conf import settings

from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = (
        "Copy the generated html API doc files to the data mount so that these can be served by an external server. This should"
        "be run as part of a deployment procedure to update API docs."
    )

    def handle(self, *args, **options):
        self.log_start()

        # Use rsync to copy folder
        src_folder = "/code/_docs/api/build/html/"
        dst_folder = os.path.join(settings.DATA_PATH, "web/api-docs/")
        subprocess.run(["rsync", "-avz", src_folder, dst_folder], check=True)  # noqa: S607

        self.log_end()
