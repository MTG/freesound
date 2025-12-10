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

import json
import logging
import os
import shutil
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone

from sounds.models import Sound, SoundAnalysis

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = """This command processed external sound analysis results and creates new SoundAnalysis objects (or updates
    existing ones) as if such analysis has been performed via the usual "orchestrate analysis" management command and
    the "process_analysis_results" task.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "results_folder",
            type=str,
            help="Path to the folder containing the external analysis results. The results folder should contain an index.json"
            "with some information about the sound analysis results that should be loaded, and a 'analysis' subfolder with the "
            "actual analysis result files structured in the same way as the main 'analysis' folder (settings.ANALYSIS_PATH). in"
            "the main freesound data directory.",
        )

        parser.add_argument(
            "-l",
            "--limit",
            action="store",
            dest="limit",
            default=None,
            help="Maximum number of sound analysis results to be loaded.",
        )

    def handle(self, *args, **options):
        results_folder = options["results_folder"]
        limit = options["limit"]

        task_results_path = os.path.join(results_folder, "task_results.json")
        if not os.path.exists(task_results_path):
            console_logger.error(f"Task results file not found at {task_results_path}. Aborting.")
            return

        with open(task_results_path, "r") as f:
            task_results = json.load(f)
        # Take only the "values" of the dict as we don't care about the task IDs
        task_results = list(task_results.values())

        if limit is not None:
            task_results = task_results[: int(limit)]

        # Filter out tasks that correspond to non-existing sounds
        all_valid_sound_ids = Sound.objects.values_list("id", flat=True)
        task_results = [tr for tr in task_results if tr["sound_id"] in all_valid_sound_ids]

        starttime = time.monotonic()
        total_done = 0
        total_loaded = 0
        total_failed_copying = 0
        N = len(task_results)
        console_logger.warning(f"Starting to load {len(task_results)} sound analysis results from {results_folder}.")

        for task_result in task_results:
            sound_id = task_result["sound_id"]

            analyzer_name = task_result["analyzer"]
            analysis_status = task_result["analysis_status"]
            analysis_time = task_result.get("analysis_time", -1)

            files_copied = False
            if analysis_status != "FA" and analysis_status != "SK":
                # Copy analysis results JSON file and log file
                id_folder = str(int(sound_id) // 1000)
                src_analysis_filepath = os.path.join(
                    results_folder, "analysis", id_folder, f"{sound_id}-{analyzer_name}.json"
                )
                target_analysis_filepath = os.path.join(
                    settings.ANALYSIS_PATH, id_folder, f"{sound_id}-{analyzer_name}.json"
                )
                src_log_filepath = os.path.join(
                    results_folder, "analysis", id_folder, f"{sound_id}-{analyzer_name}.log"
                )
                target_log_filepath = os.path.join(settings.ANALYSIS_PATH, id_folder, f"{sound_id}-{analyzer_name}.log")
                os.makedirs(os.path.dirname(target_analysis_filepath), exist_ok=True)
                try:
                    shutil.copyfile(src_analysis_filepath, target_analysis_filepath)
                    if os.path.exists(src_log_filepath):
                        shutil.copyfile(src_log_filepath, target_log_filepath)
                    files_copied = True
                except (PermissionError, FileNotFoundError) as e:
                    total_failed_copying += 1

            if not files_copied and analysis_status == "OK":
                # If files could not be coppied but they were supposed to be coppied,
                # don't create SoundAnalysis object
                pass
            else:
                # Create or update SoundAnalysis object
                try:
                    sa, _ = SoundAnalysis.objects.get_or_create(
                        sound_id=sound_id,
                        analyzer=analyzer_name,
                    )
                    sa.analysis_status = analysis_status
                    sa.analysis_time = analysis_time
                    sa.last_analyzer_finished = timezone.now()
                    sa.save(update_fields=["analysis_status", "last_analyzer_finished", "analysis_time"])
                    total_loaded += 1
                except IntegrityError:
                    # If the sound_id does not exist, an IntegrityError will be raised (should generally not happen due to previous filtering, but
                    # could be the case if during a long loading process some sounds are deleted)
                    pass

            # Report status
            total_done += 1
            elapsed = time.monotonic() - starttime
            seconds_remaining = ((N - total_done) / total_done) * elapsed if total_done > 0 else 0
            time_ramaining_label = (
                f"{seconds_remaining / 60 / 60:.4f} hours"
                if seconds_remaining > 3600
                else f"{seconds_remaining / 60:.2f} minutes"
            )
            if total_done % 1000 == 0:
                console_logger.warning(
                    f"Loaded {total_done}/{N} analyses ({total_failed_copying} failed copying). Time remaining: {time_ramaining_label} ({total_done / elapsed:.2f} analyses/second)."
                )

        console_logger.warning(
            f"Loading process finished, {total_loaded} anlysis results successfully loaded (this can include failed and skipped analyses)."
        )
