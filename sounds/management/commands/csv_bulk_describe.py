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

import gearman
import csv
import os
from django.core.management.base import BaseCommand
from sounds.models import Sound, BulkUploadProgress
from sounds.management.commands import csv_bulk_upload
from django.conf import settings

class Command(BaseCommand):
    help = 'Bulk describe sounds task'


    def handle(self, *args, **options):
        # Validate BulkUploadProgess obj with state N (initial state)
        for bulk in BulkUploadProgress.objects.filter(progress_type='N'):
            # Validate CSV file and update state
            reader = csv.reader(open(bulk.csv_path, 'rU'))
            reader.next() # Skip header
            lines = list(reader)

            cmd = csv_bulk_upload.Command()
            base_dir = os.path.join(settings.UPLOADS_PATH, str(bulk.user_id))
            valid_lines, errors = cmd.check_input_file(base_dir, lines)
            validation_errors = {}
            # validation_errors will contain the row data and the errors in the position 9
            for error in errors:
                line_number = error[0] - 2
                validation_errors.setdefault(line_number, lines[line_number]+[[]])
                validation_errors[line_number][8].append(error[1])
            bulk.validation_errors = validation_errors.values()
            bulk.sounds_valid = len(valid_lines)
            bulk.progress_type = 'V'
            bulk.save()

        # Once the user changed the state from BulkUploadProgess obj to 'S' (start) we process it
        for bulk in BulkUploadProgress.objects.filter(progress_type='S'):
            cmd = csv_bulk_upload.Command()
            opts = {'d': False,
                    'filepath': bulk.csv_path,
                    'soundsdir': os.path.join(settings.UPLOADS_PATH, str(bulk.user_id))
                    }
            cmd.handle(**opts)
            bulk.progress_type = 'F'
            bulk.save()
