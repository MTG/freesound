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
from django.contrib.auth.models import User
from django.apps import apps
from utils.tags import clean_and_split_tags
import shutil, os, csv
import utils.sound_upload


EXPECTED_HEADER_NO_USERNAME = ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name']
EXPECTED_HEADER = ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name', 'username']


class Command(BaseCommand):

    help = 'Upload many sounds at once'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to sound list')
        parser.add_argument('-d', help='Delete any sounds which already exist and add them again')
        parser.add_argument('-f', action='store_true', help='Force the import if any rows are bad, skipping bad rows')
        parser.add_argument('-s', '--soundsdir', type=str, default=None, help='Directory where the sounds are located')
        parser.add_argument('-u', '--uname', type=str, default=None,
                            help='Username of the user to assign the sounds to')
        parser.add_argument('-b', '--bulkuploadid', type=int, default=None,
                            help='Object ID for the BulkUploadProgress object where to store progress')

    @staticmethod
    def get_csv_lines(csv_file_path):
        # Get CSV contents as a list of dictionaries in which each dictionary has as rows the header values
        reader = csv.reader(open(csv_file_path, 'rU'), delimiter=';')
        header = next(reader)
        lines = [dict(zip(header, row)) for row in reader]
        return header, lines

    @staticmethod
    def check_input_file(sounds_base_dir, header, lines, username_arg=None):
        lines_ok = []
        lines_with_errors = []
        global_errors = []
        filenames_to_describe = []

        # Check headers
        if username_arg is not None and header != EXPECTED_HEADER_NO_USERNAME:
            global_errors.append('Invalid header. Header should have the following %i columns: %s'
                                 % (len(EXPECTED_HEADER_NO_USERNAME),','.join(EXPECTED_HEADER_NO_USERNAME)))
        elif username_arg is None and header != EXPECTED_HEADER:
            global_errors.append('Invalid header. Header should have the following %i columns: %s'
                                 % (len(EXPECTED_HEADER), ','.join(EXPECTED_HEADER)))

        # Check individual rows
        for n, line in enumerate(lines):
            line_errors = {}
            anyerror = False

            # Check that number of columns is ok
            if len(line) != len(EXPECTED_HEADER) and username_arg is None:
                line_errors['header'] = 'Row should have %i columns (has %i).' % (len(EXPECTED_HEADER), len(line))
                continue
            if len(line) != len(EXPECTED_HEADER_NO_USERNAME) and username_arg is not None:
                line_errors['header'] = 'Row should have %i columns (has %i).' \
                                        % (len(EXPECTED_HEADER_NO_USERNAME), len(line))
                continue

            # Check user exists
            if username_arg is not None:
                # If username provided via arg, take it from there
                username = username_arg
            else:
                # If no arg username provided, take it from CSV
                username = line['username']
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                anyerror = True
                line_errors['username'] = "User does not exist."

            # Check that audio file exists in disk and that it has not been described yet in another line
            audio_filename = line['audio_filename']
            src_path = os.path.join(sounds_base_dir, audio_filename)
            if not os.path.exists(src_path):
                anyerror = True
                line_errors['audio_filename'] = "Audio file does not exist."
            else:
                if src_path in filenames_to_describe:
                    anyerror = True
                    line_errors['audio_filename'] = "Audio file can only be described once."
                else:
                    filenames_to_describe.append(src_path)

            # Check license is valid
            license = line['license']
            License = apps.get_model('sounds', 'License')  # Import model here to avoid circular import problems
            available_licenses = License.objects.exclude(name='Sampling+').values_list('name', flat=True)
            if license not in available_licenses:
                anyerror = True
                line_errors['license'] = "Licence must be one of [%s]." % ', '.join(available_licenses)

            # Check geotag is valid
            geotag = line['geotag']
            if geotag.strip():
                # Only validate geotag if provided
                geoparts = geotag.split(',')
                if len(geoparts) == 3:
                    lat, lon, zoom = geoparts
                    try:
                        float(lat)
                        float(lon)
                        int(zoom)
                    except ValueError:
                        line_errors['geotag'] = "Geotag must be in format 'float,float,int' for latitude, " \
                                                "longitude and zoom."
                        anyerror = True
                elif len(geoparts) != 0:
                    line_errors['geotag'] = "Geotag must be in format 'float,float,int' for latitude, " \
                                            "longitude and zoom."
                    anyerror = True

            # Check tags are valid
            tags = line['tags']
            cleaned_tags = clean_and_split_tags(tags)
            if len(cleaned_tags) < 3 or len(cleaned_tags) > 30:
                line_errors['tags'] = "Incorrect number of tags (less than 3 or more than 30). " \
                                      "Remember tags must be separated by spaces."
                anyerror = True

            # Append line data to the corresponding list
            if not anyerror:
                lines_ok.append((line, n + 1))  # Add 1 to line number so first row is line 1
            else:
                lines_with_errors.append((line, line_errors, n + 1))  # Add 1 to line number so first row is line 1

        # Return lines which validated ok and lines that have errors in two separate lists. Return also a list of
        # global errors. Note that the list of lines that validated ok is in fact a list of tuples where the first
        # element is dictionary of the line fields and the second element is the line number. Similarly, the list of
        # lines with errors is in fact a list of tuples where the first element is a dictionary of the line fields,
        # the second element is a dictionary with errors (if any), and the third element is the original line number.
        return lines_ok, lines_with_errors, global_errors

    def handle(self, *args, **options):
        csv_file_path = options['filepath']
        delete_already_existing = options['d']
        force_import = options['f']
        if options['soundsdir'] is None:
            # If soundsdir is not provided, assume the same dir as the CSV file
            base_dir = os.path.dirname(csv_file_path)
        else:
            base_dir = options['soundsdir']
        username = options['uname']

        # Read and validate CSV
        header, lines = self.get_csv_lines(csv_file_path)
        lines_ok, lines_with_errors, global_errors = self.check_input_file(
            base_dir, header, lines, username_arg=username)

        # Print error messages if any
        if global_errors:
            print 'Major issues were found while validating the CSV file. Fix them and re-run the command.'
            for error in global_errors:
                print '- %s' % error
            return

        if lines_with_errors and not force_import:
            print 'The following %i lines contain invalid data. Fix them or re-run with -f to import ' \
                  'skipping these lines:' % len(lines_with_errors)
            for _, line_errs, line_no in lines_with_errors:
                errors = '; '.join(line_errs.values())
                print 'l%s: %s' % (line_no, errors)
            return

        elif lines_with_errors:
            print 'Skipping the following %i lines due to invalid data' % len(lines_with_errors)
            for _, line_errs, line_no in lines_with_errors:
                errors = '; '.join(line_errs.values())
                print 'l%s: %s' % (line_no, errors)

        # If passed as an option, get corresponding BulkUploadProgress object to store progress of command
        bulk_upload_progress_object = None
        if options['bulkuploadid']:
            BulkUploadProgress = apps.get_model('sounds', 'BulkUploadProgress')
            try:
                bulk_upload_progress_object = BulkUploadProgress.objects.get(id=options['bulkuploadid'])
            except BulkUploadProgress.DoesNotExist:
                print 'BulkUploadProgress object with id %i can\'t be found, wont store progress information.' \
                      % options['bulkuploadid']
                pass

        # Start the actual process of uploading files
        print 'Adding %i sounds to Freesound' % len(lines_ok)
        for line, line_no in lines_ok:

            # Get data from csv
            pathf = line['audio_filename']
            namef = line['name'] if line['name'].strip() else line['audio_filename']
            tagsf = line['tags']
            geotagf = line['geotag'] if line['geotag'].strip() else None
            descriptionf = line['description']
            licensef = line['license']
            packnamef = line['pack_name'] if line['pack_name'].strip() else None
            usernamef = line.get('username', username)  # If username not in CSV file, get from parameter

            # Get user object
            user = User.objects.get(username=usernamef)

            # Move sounds to the user upload directory (if sounds are not already there)
            user_uploads_directory = user.profile.locations()['uploads_dir']
            if not os.path.exists(user_uploads_directory):
                os.mkdir(user_uploads_directory)
            src_path = os.path.join(base_dir, pathf)
            dest_path = os.path.join(user_uploads_directory, os.path.basename(pathf))
            if src_path != dest_path:
                shutil.copy(src_path, dest_path)

            try:
                sound = utils.sound_upload.create_sound(
                        user=user,
                        sound_fields={
                            'name': namef,
                            'dest_path': dest_path,
                            'license': licensef,
                            'pack': packnamef,
                            'description': descriptionf,
                            'tags': tagsf,
                            'geotag': geotagf,
                        },
                        process=False,
                        remove_exists=delete_already_existing,
                )
                if bulk_upload_progress_object:
                    bulk_upload_progress_object.store_progress_for_line(line_no, sound.id)

                # Process sound and pack
                error_sending_to_process = None
                try:
                    sound.process()
                except Exception as e:
                    error_sending_to_process = str(e)
                if sound.pack:
                    sound.pack.process()

                message = 'l%i: Successfully added sound \'%s\' to Freesound.' % (line_no, sound.original_filename,)
                if error_sending_to_process is not None:
                    message += ' Sound could have not been sent to process (%s).' % error_sending_to_process
                print message

            except utils.sound_upload.NoAudioException:
                message = 'l%i: Sound for file %s can\'t be created as file does seem ot have any content.' \
                      % (line_no, dest_path,)
                print message
                if bulk_upload_progress_object:
                    bulk_upload_progress_object.store_progress_for_line(line_no, message)
            except utils.sound_upload.AlreadyExistsException:
                message = 'l%i: The file %s is already part of freesound, not uploading it.' % (line_no, dest_path,)
                print message
                if bulk_upload_progress_object:
                    bulk_upload_progress_object.store_progress_for_line(line_no, message)
            except utils.sound_upload.CantMoveException as e:
                message = 'l%i: %s.' % (line_no, e.message,)
                print message
                if bulk_upload_progress_object:
                    bulk_upload_progress_object.store_progress_for_line(line_no, message)
            except Exception:
                # If another unexpected exception happens, show a message and continue with the process so that
                # other sounds can be added
                message = 'l%i: Unexpected error %s.' % (line_no, e.message,)
                print message
                if bulk_upload_progress_object:
                    bulk_upload_progress_object.store_progress_for_line(line_no, message)
