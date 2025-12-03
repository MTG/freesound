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

from django.core.management.base import BaseCommand

from utils.sound_upload import bulk_describe_from_csv


class Command(BaseCommand):
    help = "Upload many sounds at once"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str, help="Path to sound list")
        parser.add_argument("-d", help="Delete any sounds which already exist and add them again")
        parser.add_argument("-f", action="store_true", help="Force the import if any rows are bad, skipping bad rows")
        parser.add_argument("-s", "--soundsdir", type=str, default=None, help="Directory where the sounds are located")
        parser.add_argument(
            "-u", "--uname", type=str, default=None, help="Username of the user to assign the sounds to"
        )

    def handle(self, *args, **options):
        csv_file_path = options["filepath"]
        delete_already_existing = options["d"]
        force_import = options["f"]
        if options["soundsdir"] is None:
            # If soundsdir is not provided, assume the same dir as the CSV file
            sounds_base_dir = os.path.dirname(csv_file_path)
        else:
            sounds_base_dir = options["soundsdir"]
        username = options["uname"]
        bulk_describe_from_csv(csv_file_path, delete_already_existing, force_import, sounds_base_dir, username)
