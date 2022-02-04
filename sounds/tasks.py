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
from celery.decorators import task
from django.conf import settings

from sounds.models import Sound, SoundAnalysis

workers_logger = logging.getLogger("workers")


def should_store_analysis_data_in_db(analysis_data):

    def count_dict_keys_recursive(dictionary, counter=0):
        for each_key in dictionary:
            if isinstance(dictionary[each_key], dict):
                # Recursive call
                counter = count_dict_keys_recursive(dictionary[each_key], counter + 1)
            else:
                counter += 1
        return counter

    return count_dict_keys_recursive(analysis_data) <= settings.ANALYSIS_MAX_DATA_KEYS_TO_STORE_IN_DB


@task(name="process_analysis_results")
def process_analysis_results(sound_id, analyzer, status, exception=None):
    workers_logger.info("Processing analysis results of sound {} (analyzer: {}, analysis status: {})."
        .format(sound_id, analyzer, status))
    start_time = time.time()

    try:
        # Analysis happens in a different celery worker, here we just save the results in a SoundAnalysis object
        a = SoundAnalysis.objects.get(sound_id=sound_id, analyzer=analyzer)

        # Update status and queued fields. No need to update "created" as it is done automatically by Django
        a.analysis_status = status
        a.is_queued = False
        if exception:
            a.save(update_fields=['analysis_status', 'is_queued', 'created'])
            workers_logger.error("Done processing. Analysis of sound {} FAILED (analyzer: {}, analysis status: {}, "
                                 "exception: {}).".format(sound_id, analyzer, status, exception))
        else:
            # If the results of the analysis are not huge, these can be directly stored in DB using the analysis_data
            # field.
            analysis_data = a.get_analysis_data()
            if should_store_analysis_data_in_db(analysis_data):
                a.analysis_data = a.get_analysis_data()
                a.save(update_fields=['analysis_status', 'analysis_data', 'is_queued', 'created'])
            else:
                a.save(update_fields=['analysis_status', 'is_queued', 'created'])

            workers_logger.info("Done processing. Analysis results for sound {} OK (analyzer: {}, analysis status: {})."
                                .format(sound_id, analyzer, status))

    except SoundAnalysis.DoesNotExist as e:
        workers_logger.error("Can't save analysis results as SoundAnalysis object does not exist"
                             " (sound_id: {}, analyzer:{}, error: {})".format(sound_id, analyzer, e))

    except Exception as e:
        workers_logger.error("Unexpected error while saving analysis results (sound_id: {}, analyzer: {}, error: {}, "
                             "'work_time': {})".format(sound_id, analyzer, str(e), round(time.time() - start_time)))
