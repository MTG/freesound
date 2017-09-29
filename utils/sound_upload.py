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
from django.urls import reverse
from sounds.models import Sound, Pack, License, SoundLicenseHistory
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file, remove_directory_if_empty
from utils.text import slugify
from utils.mirror_files import copy_sound_to_mirror_locations, remove_empty_user_directory_from_mirror_locations, \
    remove_uploaded_file_from_mirror_locations
from django.conf import settings
from utils.cache import invalidate_template_cache
from django.contrib.auth.models import Group
from gearman.errors import ServerUnavailable


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
    '''
    This function is used by the upload handler to create a sound object with
    the information provided through sound_fields parameter.
    '''

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

        except IOError, e:
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
    sound.set_tags(sound_fields['tags'])

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
