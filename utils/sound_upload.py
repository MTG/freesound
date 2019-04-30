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
import shutil
import csv
import logging
import json
import xlrd
from django.urls import reverse
from django.contrib.auth.models import User
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file, remove_directory_if_empty
from utils.text import slugify
from utils.mirror_files import copy_sound_to_mirror_locations, remove_empty_user_directory_from_mirror_locations, \
    remove_uploaded_file_from_mirror_locations
from utils.cache import invalidate_template_cache
from django.contrib.auth.models import Group
from gearman.errors import ServerUnavailable
from django.apps import apps
from collections import defaultdict


console_logger = logging.getLogger("console")


# Classes to handle specific errors messages on calling method
class NoAudioException(Exception):
    detail = None


class AlreadyExistsException(Exception):
    detail = None


class CantMoveException(Exception):
    detail = None


def _remove_user_uploads_folder_if_empty(user):
    """
    Check if the user uploads folder is empty and removes it.
    Removes user uploads folder in the "local" disk and in mirrored disks too. 
    """
    user_uploads_dir = user.profile.locations()['uploads_dir']
    remove_directory_if_empty(user_uploads_dir)
    remove_empty_user_directory_from_mirror_locations(user_uploads_dir)


def create_sound(user, sound_fields, apiv2_client=None, process=True, remove_exists=False):
    """
    This function is used by the upload handler to create a sound object with
    the information provided through sound_fields parameter.
    """

    # Import models using apps.get_model (to avoid circular dependencies)
    Sound = apps.get_model('sounds', 'Sound')
    License = apps.get_model('sounds', 'License')
    Pack = apps.get_model('sounds', 'Pack')

    # 1 make sound object
    sound = Sound()
    sound.user = user
    sound.original_filename = sound_fields['name']
    sound.original_path = sound_fields['dest_path']
    try:
        sound.filesize = os.path.getsize(sound.original_path)
    except OSError:
        raise NoAudioException()

    license = License.objects.get(name=sound_fields['license'])
    sound.type = get_sound_type(sound.original_path)
    sound.license = license
    sound.md5 = md5file(sound.original_path)

    sound_already_exists = Sound.objects.filter(md5=sound.md5).exists()
    if sound_already_exists:
        existing_sound = Sound.objects.get(md5=sound.md5)
        if remove_exists:
            existing_sound.delete()
        else:
            msg = 'The file %s is already part of freesound and has been discarded, see <a href="%s">here</a>.' % \
                    (sound_fields['name'], reverse('sound', args=[existing_sound.user.username, existing_sound.id]))

            # Remove file (including mirror locations)
            os.remove(sound.original_path)
            remove_uploaded_file_from_mirror_locations(sound.original_path)
            _remove_user_uploads_folder_if_empty(sound.user)

            raise AlreadyExistsException(msg)

    # 2 save
    sound.save()

    # Create corresponding SoundLicenseHistory object (can't be done before Sound is saved for the first time)
    sound.set_license(license)

    # 3 move to new path
    orig = os.path.splitext(os.path.basename(sound.original_filename))[0]  # WATCH OUT!
    sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(orig))
    new_original_path = sound.locations("path")
    if sound.original_path != new_original_path:
        try:
            os.makedirs(os.path.dirname(new_original_path))
        except OSError:
            pass
        try:
            shutil.move(sound.original_path, new_original_path)

            # Check if user upload folder still has files and remove if empty
            # NOTE: we first need to remove the file from the mirror locations as we do not perform
            # a 'move' operation there.
            remove_uploaded_file_from_mirror_locations(sound.original_path)
            _remove_user_uploads_folder_if_empty(sound.user)

        except IOError as e:
            raise CantMoveException("Failed to move file from %s to %s" % (sound.original_path, new_original_path))
        sound.original_path = new_original_path
        sound.save()

    # Copy to mirror location
    copy_sound_to_mirror_locations(sound)

    # 4 create pack if it does not exist
    if 'pack' in sound_fields:
        if sound_fields['pack']:
            if Pack.objects.filter(name=sound_fields['pack'], user=user).exclude(is_deleted=True).exists():
                p = Pack.objects.get(name=sound_fields['pack'], user=user)
            else:
                p, created = Pack.objects.get_or_create(user=user, name=sound_fields['pack'])
            sound.pack = p

    # 5 create geotag objects
    if 'geotag' in sound_fields:
        # Create geotag from lat,lon,zoom text format
        if sound_fields['geotag']:
            lat, lon, zoom = sound_fields['geotag'].split(',')
            geotag = GeoTag(user=user,
                            lat=float(lat),
                            lon=float(lon),
                            zoom=int(zoom))
            geotag.save()
            sound.geotag = geotag
    else:
        # Create geotag from lat, lon, zoom separated fields (if available)
        lat = sound_fields.get('lat', None)
        lon = sound_fields.get('lon', None)
        zoom = sound_fields.get('zoom', None)
        if lat is not None and lon is not None and zoom is not None:
            geotag = GeoTag(user=user,
                            lat=float(lat),
                            lon=float(lon),
                            zoom=int(zoom))
            geotag.save()
            sound.geotag = geotag

    # 6 set description, tags
    sound.description = sound_fields['description']
    sound.set_tags(sound_fields['tags'])

    if 'is_explicit' in sound_fields:
        sound.is_explicit = sound_fields['is_explicit']

    # 6.5 set uploaded apiv2 client
    sound.uploaded_with_apiv2_client = apiv2_client

    # 7 save!
    sound.save()

    # 8 create moderation tickets if needed
    if user.profile.is_whitelisted:
        sound.change_moderation_state('OK')
    else:
        # create moderation ticket!
        sound.create_moderation_ticket()
        invalidate_template_cache("user_header", user.id)
        moderators = Group.objects.get(name='moderators').user_set.all()
        for moderator in moderators:
            invalidate_template_cache("user_header", moderator.id)

    # 9 process sound and packs
    sound.compute_crc()

    if process:
        try:
            sound.process_and_analyze(high_priority=True)

            if sound.pack:
                sound.pack.process()
        except ServerUnavailable:
            pass

    return sound


def get_csv_lines(csv_file_path):
    """
    Get the contents of a CSV file and returns a tuple (header, lines) with the header of the CSV file and the
    rest of lines as a list of dictionaries (with keys being the element sin the header).

    We currently support both CSV and EXCEL (XLS, XLSX) files, therefore all the functions and variables here that
    are named "*csv*" apply to both formats.

    NOTE: each dictionary in "lines" won't have more items than the number of items in "header" because "zip"
    function will ignore them. However it can happen that an a dictionary in "lines" has less items than the
    nuber of items in "header" if the individual row has less columns (again, "zip" will cut the mismatch
    between "header" and "row")
    """

    def xls_val_to_string(val):
        if type(val) == unicode:
            return str(val.encode('utf-8'))
        else:
            return str(val)

    if csv_file_path.endswith('.csv'):
        # Read CSV formatted file
        reader = csv.reader(open(csv_file_path, 'rU'), delimiter=',')
        header = next(reader)
        lines = [dict(zip(header, row)) for row in reader]
    elif csv_file_path.endswith('.xls') or csv_file_path.endswith('.xlsx'):
        # Read from Excel format
        wb = xlrd.open_workbook(csv_file_path)
        s = wb.sheet_by_index(0)  # Get first excel sheet
        header = s.row_values(0)
        lines = [dict(zip(header, row)) for row in
                 [[xls_val_to_string(val) for val in s.row_values(i)] for i in range(1, s.nrows)]]
    else:
        header = []
        lines = []
    return header, lines


EXPECTED_HEADER_NO_USERNAME = \
    ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name', 'is_explicit']
EXPECTED_HEADER = \
    ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name', 'is_explicit', 'username']


def validate_input_csv_file(csv_header, csv_lines, sounds_base_dir, username=None):
    """
    Reads through the lines of a CSV file containing metadata to describe (and create) new Sound objects and returns
    the list of lines after the validation process and a list of global errors (if any).

    Each element in the returned list of lines after the validation process is a dictionary which inclues the original
    line content, the cleaned line content (i.e. fields with cleaned data), and a dictionary of errors for the line
    (if any). Lines that validated ok form lines that did not validate ok can be separated by checking whether there
    are any errors for them.

    :param csv_header: header of the CSV (as returned by 'get_csv_lines' funtion above).
    :param csv_lines: lines of the CSV (as returned by 'get_csv_lines' funtion above).
    :param sounds_base_dir: directory where audio files referenced in CSV file lines should be found.
    :param username: username of the User to which sounds should be assigned to.
    :return: tuple - (lines_validated, global_errors)
    """
    lines_validated = []
    global_errors = []
    filenames_to_describe = []

    # Import required sound models using apps.get_model (to avoid circular dependencies)
    License = apps.get_model('sounds', 'License')

    # Import sound form here to avoid circular dependecy problems between sounds.models, sounds.forms and
    # utils.sound_upload.
    from sounds.forms import SoundCSVDescriptionForm

    # Check headers
    if username is not None and csv_header != EXPECTED_HEADER_NO_USERNAME:
        global_errors.append('Invalid header. Header should be: <i>%s</i>'
                             % ','.join(EXPECTED_HEADER_NO_USERNAME))
    elif username is None and csv_header != EXPECTED_HEADER:
        global_errors.append('Invalid header. Header should be: <i>%s</i>'
                             % ','.join(EXPECTED_HEADER))

    # Check that there are lines for sounds
    if len(csv_lines) == 0:
        global_errors.append('The file contains no lines with sound descriptions')

    # Check individual rows
    if not global_errors:
        for n, line in enumerate(csv_lines):
            line_errors = defaultdict(str)
            line_cleaned = None
            n_columns_is_ok = True

            # Check that number of columns is ok
            if len(line) != len(EXPECTED_HEADER) and username is None:
                line_errors['columns'] = 'Row should have %i columns but it has %i.' % (len(EXPECTED_HEADER), len(line))
                n_columns_is_ok = False

            if len(line) != len(EXPECTED_HEADER_NO_USERNAME) and username is not None:
                line_errors['columns'] = 'Row should have %i columns but it has %i.' \
                                        % (len(EXPECTED_HEADER_NO_USERNAME), len(line))
                n_columns_is_ok = False

            if n_columns_is_ok:
                # If the number of columns of the current row is ok, we can proceed to validate each individual column

                # 1) Check that user exists
                sound_username = username or line['username']
                try:
                    User.objects.get(username=sound_username)
                except User.DoesNotExist:
                    line_errors['username'] = "User does not exist."

                # 2) Check that audio file is valid, that exists in disk and that it has not been described yet in
                # CSV another line
                audio_filename = line['audio_filename']
                if not audio_filename.strip():
                    line_errors['audio_filename'] = "Invalid audio filename."
                else:
                    from accounts.forms import filename_has_valid_extension
                    if not filename_has_valid_extension(audio_filename):
                        line_errors['audio_filename'] = "Invalid file extension."
                    else:
                        src_path = os.path.join(sounds_base_dir, audio_filename)
                        if not os.path.exists(src_path):
                            line_errors['audio_filename'] = "Audio file does not exist. This should be the name of " \
                                                            "one of the audio files you <a href='%s'>previously " \
                                                            "uploaded</a>." % reverse('accounts-describe')
                        else:
                            if src_path in filenames_to_describe:
                                line_errors['audio_filename'] = "Audio file can only be described once."
                            else:
                                filenames_to_describe.append(src_path)

                # 3) Check that all the other sound fields are ok
                try:
                    license = License.objects.get(name=line['license'])
                    license_id = license.id
                    license_name = license.name
                except License.DoesNotExist:
                    license_id = 0
                    license_name = ''

                try:
                    # Make sure is_explicit value is an integer (the library we use to parse xls/xlsx files treats
                    # numbers as float and we need integer here.
                    line['is_explicit'] = int(float(line['is_explicit']))

                    # Check that is_explicit is either 0 or 1
                    if int(line['is_explicit']) not in [0, 1]:
                        line_errors['is_explicit'] = 'Invalid value. Should be "1" if sound is explicit or ' \
                                                     '"0" otherwise.'
                except ValueError:
                    line_errors['is_explicit'] = 'Invalid value. Should be "1" if sound is explicit or "0" otherwise.'

                sound_fields = {
                    'name': line['name'] or audio_filename,
                    'description': line['description'],
                    'license': license_id,
                    'tags': line['tags'],
                    'pack_name': line['pack_name'] or None,
                    'is_explicit': str(line['is_explicit']) == '1'
                }

                if line['geotag'].strip():
                    geoparts = str(line['geotag']).split(',')
                    if len(geoparts) == 3:
                        lat, lon, zoom = geoparts
                        sound_fields['lat'] = lat
                        sound_fields['lon'] = lon
                        sound_fields['zoom'] = zoom
                    else:
                        line_errors['geotag'] = "Invalid geotag format. Must be latitude, longitude and zoom " \
                                                "separated by commas (e.g. 41.40348, 2.189420, 18)."

                form = SoundCSVDescriptionForm(sound_fields)
                if not form.is_valid():
                    # If there are errors, add them to line_errors
                    for field, errors in json.loads(form.errors.as_json()).items():
                        if field in ['lat', 'lon', 'zoom']:
                            line_errors['geotag'] += ' '.join([e['message'] for e in errors])
                        else:
                            line_errors[field] = ' '.join([e['message'] for e in errors])
                    # Post-process some error so they are more user-friendly
                    if 'Enter a whole number' in line_errors['geotag'] or 'Enter a number' in line_errors['geotag']:
                        # Make geotag error messages more user-friendly when the problem is that at least one of the
                        # numbers is not formatted correctly
                        line_errors['geotag'] = "Invalid geotag format. Must be latitude, longitude and zoom " \
                                                "separated by commas (e.g. 41.40348, 2.189420, 18)."

                line_cleaned = form.cleaned_data
                line_cleaned.update({  # Update line_cleaned with the fields not returned by SoundCSVDescriptionForm
                    'username': sound_username,
                    'audio_filename': audio_filename,
                    'license': license_name,  # Overwrite license with license name as License is not JSON serializable
                    'tags': list(line_cleaned.get('tags', [])),  # Convert tags to List as Set is not JSON serializable
                })

            lines_validated.append({
                'line_no': n + 2,  # Show line number with l1 = header, l2 = first sound, and soon
                'line_original': line,
                'line_cleaned': line_cleaned,
                'line_errors': line_errors,
            })

    return lines_validated, global_errors


def bulk_describe_from_csv(csv_file_path, delete_already_existing=False, force_import=False, sounds_base_dir=None,
                           username=None, bulkupload_progress_id=None):
    """
    Reads through the lines of a CSV file containing metadata to describe (and create) new Sound objects and creates
    them if the metadata is valid.
    :param csv_file_path: filepath of the CSV file to read.
    :param delete_already_existing: if sounds thata are being created are already part of Freesound (md5 check),
    remove them before createing the new ones.
    :param force_import: ignore sounds corresponding to the CSV lines that failed validation and import the others.
    :param sounds_base_dir: directory where audio files referenced in CSV file lines should be found.
    :param username: username of the User to which sounds should be assigned to.
    :param bulkupload_progress_id: ID of the BulkUploadProgress object that should be use to store progress information
    to. If not specified, progress informaiton is not written anywhere.
    """

    # Import models using apps.get_model (to avoid circular dependencies)
    BulkUploadProgress = apps.get_model('sounds', 'BulkUploadProgress')

    # Read and validate CSV
    header, lines = get_csv_lines(csv_file_path)
    lines_validated, global_errors = validate_input_csv_file(
        csv_header=header,
        csv_lines=lines,
        sounds_base_dir=sounds_base_dir,
        username=username)

    # Print global error messages if any
    if global_errors:
        console_logger.info('Major issues were found while validating the CSV file. '
                            'Fix them and re-run the command.')
        for error in global_errors:
            console_logger.info('- %s' % error)
        return

    # Print line error messages if any
    lines_with_errors = [line for line in lines_validated if line['line_errors']]
    if lines_with_errors:
        if not force_import:
            console_logger.info('The following %i lines contain invalid data. Fix them or re-run with -f to import '
                                'skipping these lines:' % len(lines_with_errors))
        else:
            console_logger.info('Skipping the following %i lines due to invalid data' % len(lines_with_errors))
        for line in lines_with_errors:
            errors = '; '.join(line['line_errors'].values())
            console_logger.info('l%s: %s' % (line['line_no'], errors))
        if not force_import:
            return

    # If bulkupload_progress_id is not None, get corresponding BulkUploadProgress object to store progress information
    bulk_upload_progress_object = None
    if bulkupload_progress_id:
        try:
            bulk_upload_progress_object = BulkUploadProgress.objects.get(id=bulkupload_progress_id)
        except BulkUploadProgress.DoesNotExist:
            console_logger.info('BulkUploadProgress object with id %i can\'t be found, wont store progress information.'
                                % bulkupload_progress_id)

    # Start the actual process of uploading files
    lines_ok = [line for line in lines_validated if not line['line_errors']]
    console_logger.info('Adding %i sounds to Freesound' % len(lines_ok))
    for line in lines_ok:
        line_cleaned = line['line_cleaned']

        # Get user object
        user = User.objects.get(username=username or line_cleaned['username'])

        # Move sounds to the user upload directory (if sounds are not already there)
        user_uploads_directory = user.profile.locations()['uploads_dir']
        if not os.path.exists(user_uploads_directory):
            os.mkdir(user_uploads_directory)
        src_path = os.path.join(sounds_base_dir, line_cleaned['audio_filename'])
        dest_path = os.path.join(user_uploads_directory, os.path.basename(line_cleaned['audio_filename']))
        if src_path != dest_path:
            shutil.copy(src_path, dest_path)

        try:
            sound = create_sound(
                    user=user,
                    sound_fields={
                        'name': line_cleaned['name'],
                        'dest_path': dest_path,
                        'license': line_cleaned['license'],
                        'pack': line_cleaned['pack_name'],
                        'description': line_cleaned['description'],
                        'tags': line_cleaned['tags'],
                        'lat': line_cleaned['lat'],
                        'lon': line_cleaned['lon'],
                        'zoom': line_cleaned['zoom'],
                        'is_explicit': line_cleaned['is_explicit'],
                    },
                    process=False,
                    remove_exists=delete_already_existing,
            )
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line['line_no'], sound.id)

            # Process sound and pack
            error_sending_to_process = None
            try:
                sound.process_and_analyze(high_priority=True)
            except Exception as e:
                error_sending_to_process = str(e)
            if sound.pack:
                sound.pack.process()

            message = 'l%i: Successfully added sound \'%s\' to Freesound.' % (line['line_no'], sound.original_filename,)
            if error_sending_to_process is not None:
                message += ' Sound could have not been sent to process (%s).' % error_sending_to_process
            console_logger.info(message)

        except NoAudioException:
            message = 'l%i: Sound for file %s can\'t be created as file does not seem to have any content.' \
                  % (line['line_no'], dest_path,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line['line_no'], message)
        except AlreadyExistsException:
            message = 'l%i: The file %s is already part of Freesound, discarding it.' % (line['line_no'], dest_path,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line['line_no'], message)
        except CantMoveException as e:
            message = 'l%i: %s.' % (line['line_no'], e.message,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line['line_no'], message)
        except Exception as e:
            # If another unexpected exception happens, show a message and continue with the process so that
            # other sounds can be added
            message = 'l%i: Unexpected error %s.' % (line['line_no'], e.message,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line['line_no'], message)
