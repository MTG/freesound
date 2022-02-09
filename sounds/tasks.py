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
import datetime
import logging
import os
import time
from celery.decorators import task
from django.conf import settings

from sounds.models import Sound, SoundAnalysis

workers_logger = logging.getLogger("workers")


@task(name="process_analysis_results")
def process_analysis_results(sound_id, analyzer, status, analysis_time, exception=None):
    """Process the results of the analysis of a file and update the SoundAnalysis object accordingly.

    This is a celery task that gets called by the analysis workers when they finish the analysis job. This task checks
    the results and updates the corresponding SoundAnalysis object to update the status, modification date, analysis
    time, analysis data, etc...

    Args:
        sound_id (int): ID of the sound that has been analyzed
        analyzer (str): name of the analyzer that was used to analyze the sound
        status (str): status after the analysis job has finished. Should be one of "OK" for ok analysis, "FA" for
            failed analysis, or "SK" for analysis that were skipped (e.g. because a file was too long or some other
            reason decided by the analyzer).
        analysis_time (float): the time it took in seconds for the analyzer to carry out the analysis task
        exception (str): error message in case there was an error
    """
    workers_logger.info("Processing sound analysis results"
                        " (sound_id: {}, analyzer:{}, status: {})".format(sound_id, analyzer, status))
    try:
        # Analysis happens in a different celery worker, here we just save the results in a SoundAnalysis object
        a = SoundAnalysis.objects.get(sound_id=sound_id, analyzer=analyzer)

        # Update status and queued fields. No need to update "created" as it is done automatically by Django
        a.analysis_status = status
        a.analysis_time = analysis_time
        a.last_analyzer_finished = datetime.datetime.now()
        a.save(update_fields=['analysis_status', 'last_analyzer_finished', 'analysis_time'])
        if exception:
            workers_logger.error("Done processing. Analysis of sound {} FAILED (analyzer: {}, analysis status: {}, "
                                 "exception: {}).".format(sound_id, analyzer, status, exception))
        else:
            # Load analysis output to database field (following configuration  in settings.ANALYZERS_CONFIGURATION)
            a.load_analysis_data_from_file_to_db()
            # Set sound to index dirty so that the sound gets reindexed with updated analysis fields
            a.sound.mark_index_dirty(commit=True)
            workers_logger.info("Done processing sound analysis results"
                                " (sound_id: {}, analyzer:{}, status: {})".format(sound_id, analyzer, status))

    except SoundAnalysis.DoesNotExist as e:
        workers_logger.error("Can't process analysis results as SoundAnalysis object does not exist"
                             " (sound_id: {}, analyzer:{}, error: {})".format(sound_id, analyzer, e))

    except Exception as e:
        workers_logger.error("Unexpected error while processing analysis results"
                             " (sound_id: {}, analyzer: {}, error: {})".format(sound_id, analyzer, e))
