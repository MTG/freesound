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

import logging
import os
import time

from django.conf import settings  # ??
from celery.decorators import task

from sounds.models import Sound, SoundAnalysis

workers_logger = logging.getLogger("workers")


class WorkerException(Exception):
    """
    Exception raised by the worker if:
    i) the analysis/processing function takes longer than the timeout specified in settings.WORKER_TIMEOUT
    ii) the check for free disk space  before running the analysis/processing function fails
    """
    pass


def check_if_free_space(directory=settings.PROCESSING_TEMP_DIR,
                        min_disk_space_percentage=settings.WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE):
    """
    Checks if there is free disk space in the volume of the given 'directory'. If percentage of free disk space in this
    volume is lower than 'min_disk_space_percentage', this function raises WorkerException.
    :param str directory: path of the directory whose volume will be checked for free space
    :param float min_disk_space_percentage: free disk space percentage to check against
    :raises WorkerException: if available percentage of free space is below the threshold
    """
    stats = os.statvfs(directory)
    percentage_free = stats.f_bfree * 1.0 / stats.f_blocks
    if percentage_free < min_disk_space_percentage:
        raise WorkerException("Disk is running out of space, "
                              "aborting task as there might not be enough space for temp files")


@task(name="process_analysis_results")
def process_analysis_results(sound_id, analyzer, analyzer_version, result, status):
    workers_logger.info("Processing analysis results of sound {} (analyzer: {}, analyzer version: {}, analysis status: {}).".format(
        sound_id, analyzer, analyzer_version, status))
    start_time = time.time()
    try:
        check_if_free_space()
        # Analysis happens in a different celery worker, here we just save the results in a SoundAnalysis object
        sound = Sound.objects.get(id=sound_id)
        a, _ = SoundAnalysis.objects.get_or_create(sound=sound, analyzer=analyzer,
                                                   analyzer_version=analyzer_version,
                                                   analysis_data=result)
        a.set_analysis_status(status)
        workers_logger.info("Done processing analysis results for sound {} (analyzer: {}, analyzer_version: {}, analysis status: {}).".format(
            sound_id, analyzer, analyzer_version, status))
    except Sound.DoesNotExist as e:
        workers_logger.error("Failed to analyze a sound that does not exist (sound_id: {}, analyzer:{}, error: {})".format(
            sound_id, analyzer, str(e)))
    except WorkerException as e:
        workers_logger.error("WorkerException while analyzing sound (sound_id: {}, analyzer: {}, error: {}, 'work_time': {})".format(
            sound_id, analyzer, str(e), round(time.time() - start_time)))

    except Exception as e:
        workers_logger.error("Unexpected error while analyzing sound (sound_id: {}, analyzer: {}, error: {}, 'work_time': {})".format(
            sound_id, analyzer, str(e), round(time.time() - start_time)))
