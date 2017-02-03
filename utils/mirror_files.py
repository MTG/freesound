from django.conf import settings
import os
import shutil
import logging

logger = logging.getLogger('web')


def copy_files_to_mirror_locations(sound, file_types):

    # Generate a list of tuples of (source_path, destionation_path) of files that need to be copied
    source_destination_tuples = []
    for file_type in file_types:
        if file_type not in settings.MIRROR_DISK_LOCATIONS or settings.MIRROR_DISK_LOCATIONS[file_type] is None:
            continue

        if file_type == 'SOUNDS':
            for destionation_base_path in settings.MIRROR_DISK_LOCATIONS[file_type]:
                source_path = sound.locations('path')
                source_destination_tuples.append((
                    source_path,
                    source_path.replace(settings.SOUNDS_PATH, destionation_base_path)
                ))
        elif file_type == 'PREVIEWS':
            for destionation_base_path in settings.MIRROR_DISK_LOCATIONS[file_type]:
                for location_path in ['preview.HQ.mp3.path', 'preview.HQ.ogg.path',
                                      'preview.LQ.mp3.path', 'preview.LQ.ogg.path']:
                    source_path = sound.locations(location_path)
                    source_destination_tuples.append((
                        source_path,
                        source_path.replace(settings.PREVIEWS_PATH, destionation_base_path)
                    ))
        elif file_type == 'DISPLAYS':
            for destionation_base_path in settings.MIRROR_DISK_LOCATIONS[file_type]:
                for location_path in ['display.spectral.L.path', 'display.spectral.M.path',
                                      'display.wave.L.path', 'display.wave.M.path']:
                    source_path = sound.locations(location_path)
                    source_destination_tuples.append((
                        source_path,
                        source_path.replace(settings.DISPLAYS_PATH, destionation_base_path)
                    ))
        elif file_type == 'ANALYSIS':
            for destionation_base_path in settings.MIRROR_DISK_LOCATIONS[file_type]:
                for location_path in ['analysis.frames.path', 'analysis.statistics.path']:
                    source_path = sound.locations(location_path)
                    source_destination_tuples.append((
                        source_path,
                        source_path.replace(settings.ANALYSIS_PATH, destionation_base_path)
                    ))

    # Do the actual copying of the files
    for source_path, destination_path in source_destination_tuples:
        try:
            os.makedirs(os.path.dirname(destination_path))
        except OSError:  # I.e. path already exists
            pass

        try:
            shutil.copy2(source_path, destination_path)
        except IOError as e:
            # File does not exist, no permissions, etc.
            logger.error('Failed copying %s files for sound %i (%s)' % (', '.join(file_types), sound.id, str(e)))
