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
from django.conf import settings
from sounds.models import Sound, Pack, License
from utils.mirror_files import copy_sound_to_mirror_locations
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file
from utils.text import slugify
import shutil, os, csv
import utils.sound_upload


class Command(BaseCommand):

    help = 'Upload many sounds at once'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to sound list')
        parser.add_argument('-d', help='Delete any sounds which already exist and add them again')
        parser.add_argument('-f', action='store_true', help='Force the import if any rows are bad, skipping bad rows')
        parser.add_argument('-s', '--soundsdir', type=str, default='', help='Directory where the sounds are located')

    def check_input_file(self, base_dir, lines):
        errors = []
        return_lines = []
        for n, line in enumerate(lines, 2): # Count from the header
            anyerror = False
            if len(line) != 8:
                errors.append((n, 'Line does not have 8 fields'))
                anyerror = True
                continue

            pathf,namef,tagsf,geotagf,descriptionf,licensef,packnamef,usernamef = line
            try:
                User.objects.get(username=usernamef)
            except User.DoesNotExist:
                anyerror = True
                errors.append((n, "User '%s' does not exist" % usernamef))

            src_path = os.path.join(base_dir, pathf)
            if not os.path.exists(src_path):
                anyerror = True
                errors.append((n, "Source file '%s' does not exist" % pathf))

            try:
                License.objects.get(name=licensef)
            except License.DoesNotExist:
                anyerror = True
                errors.append((n, "Licence with name '%s' does not exist" % licensef))

            geoparts = geotagf.split()
            if len(geoparts) == 3:
                lat, lon, zoom = geoparts
                try:
                    float(lat)
                    float(lon)
                    int(zoom)
                except ValueError:
                    errors.append((n, "Geotag ('%s') must be in format 'float float int'" % geotagf))
                    anyerror = True
            elif len(geoparts) != 0:
                errors.append((n, "Geotag ('%s') must be in format 'float float int'" % geotagf))
                anyerror = True

            if not anyerror:
                return_lines.append(line)

        # Check format of geotags
        return return_lines, errors

    def handle(self, *args, **options):
        sound_list = options['filepath']
        print 'Importing from', sound_list

        if options['soundsdir'] == '':
            base_dir = os.path.dirname(sound_list)
        else:
            base_dir = options['soundsdir']

        delete_already_existing = options['d']
        force_import = options['d']

        reader = csv.reader(open(sound_list, 'rU'))
        reader.next() # Skip header
        lines = list(reader)

        lines_to_import, bad_lines = self.check_input_file(base_dir, lines)
        if bad_lines and not force_import:
            print 'Some lines contain invalid data. Fix them or re-run with -f to import skipping these lines:'
            for lineno, error in bad_lines:
                print 'l%s: %s' % (lineno, error)
            return
        elif bad_lines:
            print 'Skipping the following lines due to invalid data'
            for lineno, error in bad_lines:
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
