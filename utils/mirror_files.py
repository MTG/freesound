from django.conf import settings
import os
import shutil
import logging
import errno

logger = logging.getLogger('web')


def copy_files_to_mirror_locations(sound, source_location_keys, source_base_path, destination_base_paths):

    if destination_base_paths is None:
        return

    # Generate a list of tuples of (source_path, destionation_path) of files that need to be copied
    source_destination_tuples = []
    for destination_base_path in destination_base_paths:
        for location_path in source_location_keys:
            source_path = sound.locations(location_path)
            source_destination_tuples.append((
                source_path,
                source_path.replace(source_base_path, destination_base_path)
            ))

    # Do the actual copying of the files
    for source_path, destination_path in source_destination_tuples:
        try:
            path = os.path.dirname(destination_path)
            os.makedirs(path)
        except OSError as e:  # I.e. path already exists
            if e.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

        try:
            shutil.copy2(source_path, destination_path)
        except IOError as e:
            # File does not exist, no permissions, etc.
            logger.error('Failed copying %s (%s)' % (source_path, str(e)))


def copy_sound_to_mirror_locations(sound):
    copy_files_to_mirror_locations(sound, ['path'], settings.SOUNDS_PATH, settings.MIRROR_SOUNDS)


def copy_previews_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['preview.HQ.mp3.path', 'preview.HQ.ogg.path', 'preview.LQ.mp3.path', 'preview.LQ.ogg.path'],
        settings.PREVIEWS_PATH, settings.MIRROR_PREVIEWS)


def copy_displays_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['display.spectral.L.path', 'display.spectral.M.path', 'display.wave.L.path', 'display.wave.M.path'],
        settings.DISPLAYS_PATH, settings.MIRROR_DISPLAYS)


def copy_analysis_to_mirror_locations(sound):
    copy_files_to_mirror_locations(
        sound, ['analysis.frames.path', 'analysis.statistics.path'], settings.ANALYSIS_PATH, settings.MIRROR_ANALYSIS)
