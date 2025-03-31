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
import glob
import logging
import os
import time

from django.conf import settings
from django.utils import timezone

from utils.management_commands import LoggingBaseCommand


console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = '''Remove analysis temp PCM conversion files which are left in disk from analyzers and have not been used 
    for a while. We normally keep these files in disk in case we need to re-analyze a file or analyze a file with 
    different analyzers in a short period of time and so we can reuse the converted file. However old files can be safely 
    deleted and will be recreated if need be.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action="store_true",
            help="Using this files will not be deleted but only information printed on screen.")

    def handle(self, *args, **options):
        self.log_start()
        
        data_to_log = {}
        wav_files_in_analysis_path = glob.glob(settings.ANALYSIS_PATH + '**/*.wav')
        files_to_remove = []
        for filepath in wav_files_in_analysis_path:
            try:
                datetime.datetime.strptime(time.ctime(), "%a %b %d %H:%M:%S %Y")
                modification_time = datetime.datetime.strptime(time.ctime(os.path.getmtime(filepath)), "%c")
                date_cutoff = \
                    timezone.now() - datetime.timedelta(
                        hours=settings.ORCHESTRATE_ANALYSIS_MAX_TIME_CONVERTED_FILES_IN_DISK)
                if modification_time < date_cutoff:
                    files_to_remove.append(filepath)
            except OSError:
                # This can happen if the wav file was a tmp file that was renamed while command runs
                pass
        data_to_log['converted_files_to_remove'] = len(files_to_remove)
        console_logger.info('Will remove {} converted PCM files because of them being in disk for '
                            'too long'.format(len(files_to_remove)))
        if not options['dry_run']:
            for filepath in files_to_remove:
                try:
                    os.remove(filepath)
                except Exception as e:
                    console_logger.info(f'Error deleting file {filepath}: {e}')

        self.log_end(data_to_log)
