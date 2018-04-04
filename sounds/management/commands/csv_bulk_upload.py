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
        parser.add_argument('-s', '--soundsdir', type=str, default='', help='Directory where the sounds are located')

    @staticmethod
    def get_csv_lines(csv_file_path):
        # Get CSV contents as a list of dictionaries in which each dictionary has as rows the header values
        reader = csv.reader(open(csv_file_path, 'rU'), delimiter=';')
        header = next(reader)
        lines = [dict(zip(header, row)) for row in reader]
        return header, lines

    @staticmethod
    def check_input_file(sounds_base_dir, header, lines, skip_username_check=False):
        lines_ok = []
        lines_with_errors = []
        global_errors = []
        filenames_to_describe = []

        # Check headers
        if (skip_username_check and header != EXPECTED_HEADER_NO_USERNAME) or \
                (not skip_username_check and header != EXPECTED_HEADER):
            global_errors.append('CSV file has wrong header.')

        # Check individual rows
        for n, line in enumerate(lines):
            line_errors = {}
            anyerror = False

            # Check that number of columns is ok
            if len(line) != len(EXPECTED_HEADER) and not skip_username_check:
                line_errors['header'] = 'Row should have %i columns (has %i).' % (len(EXPECTED_HEADER), len(line))
                continue
            if len(line) != len(EXPECTED_HEADER_NO_USERNAME) and skip_username_check:
                line_errors['header'] = 'Row should have %i columns (has %i).' \
                                        % (len(EXPECTED_HEADER_NO_USERNAME), len(line))
                continue

            # Check user exists
            if not skip_username_check:
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
            geoparts = geotag.split()
            if len(geoparts) == 3:
                lat, lon, zoom = geoparts
                try:
                    float(lat)
                    float(lon)
                    int(zoom)
                except ValueError:
                    line_errors['geotag'] = "Geotag must be in format 'float float int' for latitude, " \
                                            "longitude and zoom."
                    anyerror = True
            elif len(geoparts) != 0:
                line_errors['geotag'] = "Geotag must be in format 'float float int' for latitude, " \
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
                lines_ok.append(line)
            else:
                lines_with_errors.append((line, line_errors))

        # Return lines which validated ok and lines that have errors in two separate lists. Return also a list of
        # global errors. Note that the list of lines with errors is in fact a list of tuples where the first element
        # of each tuple is a dictionary of the line fields and the second element is a dictionary with errors (if any)
        # for each line field.
        return lines_ok, lines_with_errors, global_errors

    def handle(self, *args, **options):
        sound_list = options['filepath']
        print 'Importing from', sound_list

        if options['soundsdir'] == '':
            base_dir = os.path.dirname(sound_list)
        else:
            base_dir = options['soundsdir']

        delete_already_existing = options['d']
        force_import = options['d']

        header, lines = self.get_csv_lines(sound_list)

        lines_to_import, bad_lines, global_errors = self.check_input_file(base_dir, header, lines)
        if bad_lines and not force_import:
            print 'Some lines contain invalid data. Fix them or re-run with -f to import skipping these lines:'
            for lineno, error, field in bad_lines:
                print 'l%s: %s' % (lineno, error)
            return
        elif bad_lines:
            print 'Skipping the following lines due to invalid data'
            for lineno, error, field in bad_lines:
                print 'l%s: %s' % (lineno, error)

        for line in lines_to_import:
            # 0 get data from csv
            pathf,namef,tagsf,geotagf,descriptionf,licensef,packnamef,usernamef = line
            user = User.objects.get(username=usernamef)

            # 1 create dir and move sound to dir
            directory = user.profile.locations()['uploads_dir']
            if not os.path.exists(directory):
                os.mkdir(directory)

            src_path = os.path.join(base_dir, pathf)
            dest_path = os.path.join(directory, os.path.basename(pathf))

            if src_path != dest_path:
                shutil.copy(src_path, dest_path)

            sound_fields = {
                'name': namef,
                'dest_path': dest_path,
                'license': licensef,
                'pack': packnamef,
                'description': descriptionf,
                'tags': tagsf.split(),
                'geotag': geotagf
            }

            try:
                sound = utils.sound_upload.create_sound(
                        user,
                        sound_fields,
                        process=False,
                        remove_exists=delete_already_existing
                )

                # Process
                try:
                    sound.process()
                except Exception as e:
                    print 'Sound with id %s could not be scheduled. (%s)' % (sound.id, str(e))

                if sound.pack:
                    sound.pack.process()

                print 'Successfully uploaded sound ' + sound.original_filename

            except utils.sound_upload.NoAudioException:
                continue
            except utils.sound_upload.AlreadyExistsException:
                print 'The file %s is already part of freesound, not uploading it' % (dest_path,)
                continue
            except utils.sound_upload.CantMoveException as e:
                print e.message
