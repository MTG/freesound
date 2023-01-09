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
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


def remove_folder(folderpath):
    try:
        # First delete files inside folder
        for filename in os.listdir(folderpath):
            os.remove(os.path.join(folderpath, filename))        
        # Then delete the folder itself 
        shutil.rmtree(folderpath)
    except Exception as e:
        console_logger.error('ERROR removing folder {}: {}'.format(folderpath, e))


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
        }

        one_day_ago = datetime.datetime.today() - datetime.timedelta(days=1)
        one_year_ago = datetime.datetime.today() - datetime.timedelta(days=365)

        # Clean files from tmp_uploads which are olden than a day
        for filename in os.listdir(settings.FILE_UPLOAD_TEMP_DIR):
            filepath = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, filename)
            if datetime.datetime.fromtimestamp(os.path.getmtime(filepath)) < one_day_ago:
                # Delete sound
                console_logger.info('Deleting file {}'.format(filepath))
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
                    if all([datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folderpath, filename))) < one_day_ago for filename in files_in_folder]):
                        should_delete = True
                if should_delete:
                    # Delete directory and contents
                    console_logger.info('Deleting directory {}'.format(folderpath))
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
                    # NOTE: add u''.format(x) below to avoid issues with filenames with non-ascii characters. This can probably be removed when fully migrating to py3
                    if all([datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folderpath, u''.format(sound_filename)))) < one_year_ago for sound_filename in files_in_folder]):
                        should_delete = True
                if should_delete:
                    # Delete directory and contents
                    console_logger.info('Deleting directory {}'.format(folderpath))
                    cleaned_files['uploads'] += 1
                    if not options['dry_run']:
                        remove_folder(folderpath)
                
        self.log_end(cleaned_files)
