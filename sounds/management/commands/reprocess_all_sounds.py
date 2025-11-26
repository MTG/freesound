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

from django.conf import settings
from django.utils import timezone

from freesound.celery import get_queues_task_counts
from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """Progressively reprocesses all sounds in the database and replaces their images and preview files. This command is 
    expected to be run multiple times until all sounds have been processed. The progress of the reprocessing task is saved using
    in a file in the server which uses the parameter "-id" in its name. Multiple executions of this command with the same ID will
    therefore continue the reprocessing task from where it was left.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--reprocessing-id",
            action="store",
            dest="reprocessing-id",
            help="Unique ID for the reprocessing task. This is used to store information about the progress of the reprocessing "
            "task across multiple runs of the same command.",
        )

        parser.add_argument(
            "--limit",
            action="store",
            dest="limit",
            default=1000,
            help="Maximum number of sounds in the processing queue (it will only send new sounds until the queue is filled "
            "with this number).",
        )

        parser.add_argument(
            "--max-sound-id",
            action="store",
            dest="max-sound-id",
            default=999999999,
            help="The biggest sound ID which should be re-processed.",
        )

        parser.add_argument(
            "--skip-images", action="store_true", help="Don't run the waveform/spectrogram generation step."
        )

        parser.add_argument("--skip-previews", action="store_true", help="Don't run the mp3/ogg generation step.")

    def handle(self, *args, **options):
        self.log_start()
        queues_counts_dict = {item[0]: item[1] + item[2] for item in get_queues_task_counts()}
        n_sounds_currently_in_processing = queues_counts_dict[settings.CELERY_SOUND_PROCESSING_QUEUE_NAME]
        limit = int(options["limit"])
        max_sounds_to_send = limit - n_sounds_currently_in_processing
        n_sent = 0
        last_reprocessed_sound_id = 0
        reprocessing_progress = []
        num_sounds_failed_processing_before_command_run = Sound.objects.filter(processing_state="FA").count()
        if max_sounds_to_send <= 0:
            console_logger.info(
                f"Not sending any sounds to the queue as it is already full (limit: {limit}, "
                f"currently in queue: {n_sounds_currently_in_processing})"
            )
        else:
            progress_file_path = os.path.join(
                settings.DATA_PATH, f"reprocessing_progress_{options['reprocessing-id']}.json"
            )
            if os.path.exists(progress_file_path):
                reprocessing_progress = json.load(open(progress_file_path))
                last_reprocessed_sound_id = reprocessing_progress[-1]["last_sound_id"]
            sound_ids_to_reprocess = Sound.objects.filter(
                id__gt=last_reprocessed_sound_id, id__lte=int(options["max-sound-id"])
            ).order_by("id")[:max_sounds_to_send]
            if sound_ids_to_reprocess == 0:
                # All sounds have been reprocessed!
                console_logger.info("Not sending any sounds to the queue as all sounds have been reprocessed!")
            else:
                # Send sounds to processing
                console_logger.info(f"Will send {sound_ids_to_reprocess.count()} sounds to processing queue...")
                for sound in sound_ids_to_reprocess:
                    sound.process(
                        skip_previews=options.get("skip-previews", False),
                        skip_displays=options.get("skip-images", False),
                        force=True,
                    )
                    n_sent += 1
                    last_reprocessed_sound_id = sound.id
                # Save current progress
                console_logger.info(
                    f"{n_sent} sounds sent to processing queue, last sound ID: {last_reprocessed_sound_id}"
                )
                reprocessing_progress.append({"last_sound_id": last_reprocessed_sound_id, "date": str(timezone.now())})
                json.dump(reprocessing_progress, open(progress_file_path, "w"))

        self.log_end(
            {
                "n_sent_to_processing": n_sent,
                "last_reprocessed_sound_id": last_reprocessed_sound_id,
                "num_sounds_failed_processing_before_command_run": num_sounds_failed_processing_before_command_run,
            }
        )
