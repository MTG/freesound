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
import os
import shutil

from django.conf import settings
from django.utils import timezone
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


def remove_folder(folderpath, recursively=False):
    try:
        if not recursively:
            # First delete files inside folder
            for filename in os.listdir(folderpath):
                os.remove(os.path.join(folderpath, filename))        
        # Then delete the folder itself 
        shutil.rmtree(folderpath)
    except Exception as e:
        console_logger.info(f'ERROR removing folder {folderpath}: {e}')


class Command(LoggingBaseCommand):
    help = "Clean old audio files from the data volume which are no longer needed. Use --dry-run for a 'fake' pass."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action="store_true",
            help="Using this flag files will not be deleted but only information printed on screen.")

    def handle(self, **options):
        self.log_start()
        cleaned_files = {
            'tmp_uploads': 0,
            'tmp_processing': 0,
            'uploads': 0,
            'processing_before_describe': 0
        }

        one_day_ago = timezone.now() - datetime.timedelta(days=1)
        one_year_ago = timezone.now() - datetime.timedelta(days=365)

        # Clean files from tmp_uploads which are olden than a day
        for filename in os.listdir(settings.FILE_UPLOAD_TEMP_DIR):
            filepath = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, filename)
            if datetime.datetime.fromtimestamp(os.path.getmtime(filepath), tz=datetime.timezone.utc) < one_day_ago:
                # Delete sound
                console_logger.info(f'Deleting file {filepath}')
                cleaned_files['tmp_uploads'] += 1
                if not options['dry_run']:
                    os.remove(filepath)

        # Clean folders from tmp_processing that are empty or folders in which all files are older than a day
        for filename in os.listdir(settings.PROCESSING_TEMP_DIR):
            folderpath = os.path.join(settings.PROCESSING_TEMP_DIR, filename)
            if os.path.isdir(folderpath):
                should_delete = False
                files_in_folder = os.listdir(folderpath)
                if not files_in_folder:
                    should_delete = True
                else:
                    if all([datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folderpath, filename)), tz=datetime.timezone.utc) < one_day_ago for filename in files_in_folder]):
                        should_delete = True
                if should_delete:
                    # Delete directory and contents
                    console_logger.info(f'Deleting directory {folderpath}')
                    cleaned_files['tmp_processing'] += 1
                    if not options['dry_run']:
                        remove_folder(folderpath)

        # Clean folders from uploads that are empty or folders in which all files are older than a year
        for filename in os.listdir(settings.UPLOADS_PATH):
            folderpath = os.path.join(settings.UPLOADS_PATH, filename)
            if os.path.isdir(folderpath):
                should_delete = False
                files_in_folder = os.listdir(folderpath)
                if not files_in_folder:
                    should_delete = True
                else:
                    if all([datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folderpath, sound_filename)), tz=datetime.timezone.utc) < one_year_ago for sound_filename in files_in_folder]):
                        should_delete = True
                if should_delete:
                    # Delete directory and contents
                    console_logger.info(f'Deleting directory {folderpath}')
                    cleaned_files['uploads'] += 1
                    if not options['dry_run']:
                        remove_folder(folderpath)

        # Clean folders from processing_before_describe which don't have a parallel folder in uploads
        for filename in os.listdir(settings.PROCESSING_BEFORE_DESCRIPTION_DIR):
            folderpath = os.path.join(settings.PROCESSING_BEFORE_DESCRIPTION_DIR, filename)
            corresponding_folderpath_in_uploads = os.path.join(settings.UPLOADS_PATH, filename)
            if not os.path.exists(corresponding_folderpath_in_uploads):
                console_logger.info(f'Deleting directory {folderpath}')
                cleaned_files['processing_before_describe'] += 1
                if not options['dry_run']:
                    remove_folder(folderpath, recursively=True)

                
        self.log_end(cleaned_files)
