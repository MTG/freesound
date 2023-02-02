from django.conf import settings
import os
import shutil
import subprocess
import logging
from utils.filesystem import remove_directory_if_empty

web_logger = logging.getLogger('web')


def copy_files(source_destination_tuples):
    for source_path, destination_path in source_destination_tuples:
        if settings.LOG_START_AND_END_COPYING_FILES:
            web_logger.info('Started copying file {} to {}'.format(source_path, destination_path))

        if '@' in destination_path:
            # The destination path is in a remote server, use scp
            try:
                subprocess.check_output(f'rsync -e "ssh -o StrictHostKeyChecking=no  -i /ssh_fsweb/cdn-ssh-key-fsweb" -aq --rsync-path="mkdir -p {os.path.dirname(destination_path)} && rsync" {source_path} {os.path.dirname(destination_path)}/', stderr=subprocess.STDOUT, shell=True)
                if settings.LOG_START_AND_END_COPYING_FILES:
                    web_logger.info('Finished copying file {} to {}'.format(source_path, destination_path))
            except subprocess.CalledProcessError as e:            
                web_logger.error('Failed copying {} ({}: {})'.format(source_path, str(e), e.output))
        else:
            # The destioantion path is a local volume
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            try:
                shutil.copy2(source_path, destination_path)
                if settings.LOG_START_AND_END_COPYING_FILES:
                    web_logger.info('Finished copying file {} to {}'.format(source_path, destination_path))
            except OSError as e:
                # File does not exist, no permissions, etc.
                web_logger.error('Failed copying {} ({})'.format(source_path, str(e)))


def copy_files_to_mirror_locations(object, source_location_keys, source_base_path, destination_base_paths):

    if destination_base_paths is None:
        return

    # Generate a list of tuples of (source_path, destionation_path) of files that need to be copied
    source_destination_tuples = []
    for destination_base_path in destination_base_paths:
        for location_path in source_location_keys:
            source_path = object.locations(location_path)
            source_destination_tuples.append((
                source_path,
                source_path.replace(source_base_path, destination_base_path)
            ))

    copy_files(source_destination_tuples)  # Do the actual copying of the files


def copy_uploaded_file_to_mirror_locations(source_file_path):
    source_destination_tuples = []
    if settings.MIRROR_UPLOADS:
        for destination_base_path in settings.MIRROR_UPLOADS:
            source_destination_tuples.append((
                source_file_path,
                source_file_path.replace(settings.UPLOADS_PATH, destination_base_path)
            ))
        copy_files(source_destination_tuples)


def remove_uploaded_file_from_mirror_locations(source_file_path):
    source_destination_tuples = []
    if settings.MIRROR_UPLOADS:
        for destination_base_path in settings.MIRROR_UPLOADS:
            source_destination_tuples.append((
                source_file_path,
                source_file_path.replace(settings.UPLOADS_PATH, destination_base_path)
            ))
        for _, destination_path in source_destination_tuples:
            try:
                os.remove(destination_path)
            except OSError as e:
                # File does not exist, no permissions, etc.
                web_logger.error('Failed deleting {} ({})'.format(destination_path, str(e)))


def remove_empty_user_directory_from_mirror_locations(user_uploads_path):
    if settings.MIRROR_UPLOADS:
        for destination_base_path in settings.MIRROR_UPLOADS:
            remove_directory_if_empty(user_uploads_path.replace(settings.UPLOADS_PATH, destination_base_path))


def copy_sound_to_mirror_locations(sound):
    copy_files_to_mirror_locations(sound, ['path'], settings.SOUNDS_PATH, settings.MIRROR_SOUNDS)


def copy_previews_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['preview.HQ.mp3.path', 'preview.HQ.ogg.path', 'preview.LQ.mp3.path', 'preview.LQ.ogg.path'],
        settings.PREVIEWS_PATH, settings.MIRROR_PREVIEWS)


def copy_displays_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['display.spectral.L.path', 'display.spectral.M.path',
                'display.wave.L.path', 'display.wave.M.path',
                'display.spectral_bw.L.path', 'display.spectral_bw.M.path',
                'display.wave_bw.L.path', 'display.wave_bw.M.path'],
        settings.DISPLAYS_PATH, settings.MIRROR_DISPLAYS)


def copy_analysis_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['analysis.frames.path', 'analysis.statistics.path'], settings.ANALYSIS_PATH, settings.MIRROR_ANALYSIS)


def copy_avatar_to_mirror_locations(profile):
    copy_files_to_mirror_locations(
        profile, ['avatar.L.path', 'avatar.M.path', 'avatar.S.path'], settings.AVATARS_PATH, settings.MIRROR_AVATARS)
