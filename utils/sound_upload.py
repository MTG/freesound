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
from django.urls import reverse
from django.contrib.auth.models import User
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file, remove_directory_if_empty
from utils.text import slugify
from utils.mirror_files import copy_sound_to_mirror_locations, remove_empty_user_directory_from_mirror_locations, \
    remove_uploaded_file_from_mirror_locations
from utils.cache import invalidate_template_cache
from utils.tags import clean_and_split_tags
from django.contrib.auth.models import Group
from gearman.errors import ServerUnavailable
from django.apps import apps


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
            msg = 'The file %s is already part of freesound and has been discarded, see <a href="%s">here</a>' % \
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
    # format: lat#lon#zoom
    if 'geotag' in sound_fields:
        if sound_fields['geotag']:
            lat, lon, zoom = sound_fields['geotag'].split(',')
            geotag = GeoTag(user=user,
                lat=float(lat),
                lon=float(lon),
                zoom=int(zoom))
            geotag.save()
            sound.geotag = geotag

    # 6 set description, tags
    sound.description = sound_fields['description']
    tags = sound_fields['tags']
    if type(tags) is not set:  # If tags have not been cleaned and splitted, do it now
        tags = clean_and_split_tags(sound_fields['tags'])
    sound.set_tags(tags)

    if 'is_explicit' in sound_fields:
        sound.is_explicit = sound_fields['is_explicit']

    # 6.5 set uploaded apiv2 client
    sound.uploaded_with_apiv2_client = apiv2_client

    # 7 save!
    sound.save()

    # 8 create moderation tickets if needed
    if user.profile.is_whitelisted:
        sound.change_moderation_state('OK', do_not_update_related_stuff=True)
    else:
        # create moderation ticket!
        sound.create_moderation_ticket()
        invalidate_template_cache("user_header", user.id)
        moderators = Group.objects.get(name='moderators').user_set.all()
        for moderator in moderators:
            invalidate_template_cache("user_header", moderator.id)

    # 9 proces sound and packs
    try:
        sound.compute_crc()
    except:
        pass

    if process:
        try:
            sound.process()

            if sound.pack:
                sound.pack.process()
        except ServerUnavailable:
            pass

    return sound


def get_csv_lines(csv_file_path):
    """
    Get the contents of a CSV file and returns a tuple (header, lines) with the header of the CSV file and the
    rest of lines as a list of dictionaries (with keys being the element sin the header).

    NOTE: each dictionary in "lines" won't have more items than the number of items in "header" because "zip"
    function will ignore them. However it can happen that an a dictionary in "lines" has less items than the
    nuber of items in "header" if the individual row has less columns (again, "zip" will cut the mismatch
    between "header" and "row")
    """
    reader = csv.reader(open(csv_file_path, 'rU'), delimiter=';')
    header = next(reader)
    lines = [dict(zip(header, row)) for row in reader]
    return header, lines


EXPECTED_HEADER_NO_USERNAME = ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name']
EXPECTED_HEADER = ['audio_filename', 'name', 'tags', 'geotag', 'description', 'license', 'pack_name', 'username']


def validate_input_csv_file(csv_header, csv_lines, sounds_base_dir, username=None):
    """
    Reads through the lines of a CSV file containing metadata to describe (and create) new Sound objects and returns
    the lines that are ok, the lines that contain errors and a list of global errors (if any).

    This function returns the lines which validated ok, the lines that have errors and the global errors in three
    separate lists. The list of lines that validated ok is in fact a list of tuples where the first
    element is the dictionary of the line fields and the second element is the line number. Similarly, the list of
    lines with errors is in fact a list of tuples where the first element is a dictionary of the line fields,
    the second element is a dictionary with errors (if any), and the third element is the line number. The list of
    global errors is a simple list of strings describing each error (if any).

    :param csv_header: header of the CSV (as returned by 'get_csv_lines' funtion above).
    :param csv_lines: lines of the CSV (as returned by 'get_csv_lines' funtion above).
    :param sounds_base_dir: directory where audio files referenced in CSV file lines should be found.
    :param username: username of the User to which sounds should be assigned to.
    :return: tuple - (lines_ok, lines_with_errors, global_errors)
    """
    lines_ok = []
    lines_with_errors = []
    global_errors = []
    filenames_to_describe = []

    # Import models using apps.get_model (to avoid circular dependencies)
    License = apps.get_model('sounds', 'License')

    # Check headers
    if username is not None and csv_header != EXPECTED_HEADER_NO_USERNAME:
        global_errors.append('Invalid header. Header should have the following %i columns: %s'
                             % (len(EXPECTED_HEADER_NO_USERNAME), ','.join(EXPECTED_HEADER_NO_USERNAME)))
    elif username is None and csv_header != EXPECTED_HEADER:
        global_errors.append('Invalid header. Header should have the following %i columns: %s'
                             % (len(EXPECTED_HEADER), ','.join(EXPECTED_HEADER)))

    # Check individual rows
    if not global_errors:
        for n, line in enumerate(csv_lines):
            line_errors = {}
            anyerror = False
            n_columns_is_ok = True

            # Check that number of columns is ok
            if len(line) != len(EXPECTED_HEADER) and username is None:
                line_errors['columns'] = 'Row should have %i columns (has %i).' % (len(EXPECTED_HEADER), len(line))
                n_columns_is_ok = False

            if len(line) != len(EXPECTED_HEADER_NO_USERNAME) and username is not None:
                line_errors['columns'] = 'Row should have %i columns (has %i).' \
                                        % (len(EXPECTED_HEADER_NO_USERNAME), len(line))
                n_columns_is_ok = False

            if n_columns_is_ok:
                # If the number of columns of the current row is ok, we can proceed to validate each individual
                # column

                # Check user exists
                if username is None:
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
            if not anyerror and n_columns_is_ok:
                lines_ok.append((line, n + 1))  # Add 1 to line number so first row is line 1
            else:
                lines_with_errors.append((line, line_errors, n + 1))  # Add 1 to line number so first row is line 1

    return lines_ok, lines_with_errors, global_errors


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
    lines_ok, lines_with_errors, global_errors = validate_input_csv_file(
        csv_header=header,
        csv_lines=lines,
        sounds_base_dir=sounds_base_dir,
        username=username)

    # Print error messages if any
    if global_errors:
        console_logger.info('Major issues were found while validating the CSV file. '
                            'Fix them and re-run the command.')
        for error in global_errors:
            console_logger.info('- %s' % error)
        return

    if lines_with_errors and not force_import:
        console_logger.info('The following %i lines contain invalid data. Fix them or re-run with -f to import '
                            'skipping these lines:' % len(lines_with_errors))
        for _, line_errs, line_no in lines_with_errors:
            errors = '; '.join(line_errs.values())
            console_logger.info('l%s: %s' % (line_no, errors))
        return

    elif lines_with_errors:
        console_logger.info('Skipping the following %i lines due to invalid data' % len(lines_with_errors))
        for _, line_errs, line_no in lines_with_errors:
            errors = '; '.join(line_errs.values())
            console_logger.info('l%s: %s' % (line_no, errors))

    # If passed as an option, get corresponding BulkUploadProgress object to store progress of command
    bulk_upload_progress_object = None
    if bulkupload_progress_id:
        try:
            bulk_upload_progress_object = BulkUploadProgress.objects.get(id=bulkupload_progress_id)
        except BulkUploadProgress.DoesNotExist:
            console_logger.info('BulkUploadProgress object with id %i can\'t be found, wont store progress information.'
                        % bulkupload_progress_id)

    # Start the actual process of uploading files
    console_logger.info('Adding %i sounds to Freesound' % len(lines_ok))
    for line, line_no in lines_ok:

        # Get data from csv
        pathf = line['audio_filename']
        namef = line['name'] if line['name'].strip() else line['audio_filename']
        tagsf = line['tags']
        geotagf = line['geotag'] if line['geotag'].strip() else None
        descriptionf = line['description']
        licensef = line['license']
        packnamef = line['pack_name'] if line['pack_name'].strip() else None
        if username is not None:
            usernamef = username  # If username is given via parameter, take that username
        else:
            usernamef = line['username']  # Otherwise take username from CSV file

        # Get user object
        user = User.objects.get(username=usernamef)

        # Move sounds to the user upload directory (if sounds are not already there)
        user_uploads_directory = user.profile.locations()['uploads_dir']
        if not os.path.exists(user_uploads_directory):
            os.mkdir(user_uploads_directory)
        src_path = os.path.join(sounds_base_dir, pathf)
        dest_path = os.path.join(user_uploads_directory, os.path.basename(pathf))
        if src_path != dest_path:
            shutil.copy(src_path, dest_path)

        try:
            sound = create_sound(
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
            console_logger.info(message)

        except NoAudioException:
            message = 'l%i: Sound for file %s can\'t be created as file does not seem to have any content.' \
                  % (line_no, dest_path,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line_no, message)
        except AlreadyExistsException:
            message = 'l%i: The file %s is already part of freesound, not uploading it.' % (line_no, dest_path,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line_no, message)
        except CantMoveException as e:
            message = 'l%i: %s.' % (line_no, e.message,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line_no, message)
        except Exception as e:
            # If another unexpected exception happens, show a message and continue with the process so that
            # other sounds can be added
            message = 'l%i: Unexpected error %s.' % (line_no, e.message,)
            console_logger.info(message)
            if bulk_upload_progress_object:
                bulk_upload_progress_object.store_progress_for_line(line_no, message)
