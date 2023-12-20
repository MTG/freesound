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

from django.conf import settings

from freesound.celery import get_queues_task_counts
from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = """Gets a list of sounds that failed processing (or did not fininsh processing successfully) and re-sends them to processing"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action="store_true",
            help="Using this jobs will not be triggered but only information printed on screen."
        )

    def handle(self, *args, **options):
        self.log_start()

        # Get IDs of sounds that failed
        failed_ids = list(Sound.objects.filter(processing_state="FA").values_list('id', flat=True))

        # If there are no sounds in the queue, send also sounds marked as pending/queued/currently processing
        other_ids = []
        queues_counts_dict = {item[0]: item[1] + item[2] for item in get_queues_task_counts()}
        n_sounds_processing_in_rabbitmq_queue = queues_counts_dict[settings.CELERY_SOUND_PROCESSING_QUEUE_NAME]
        if n_sounds_processing_in_rabbitmq_queue == 0:
            pending_ids = list(Sound.objects.filter(processing_state="PE").values_list('id', flat=True))
            queued_in_db_ids = list(Sound.objects.filter(processing_ongoing_state="QU").values_list('id', flat=True))
            processing_id_db_ids = list(
                Sound.objects.filter(processing_ongoing_state="PR").values_list('id', flat=True)
            )
            other_ids = pending_ids + queued_in_db_ids + processing_id_db_ids

        # Send the sounds
        combined_ids = list(set(failed_ids + other_ids))
        qs = Sound.objects.filter(id__in=combined_ids)
        console_logger.info(f'Will send {qs.count()} sounds to processing')
        n_sent = 0
        for sound in qs:
            if not options['dry_run']:
                was_sent = sound.process()
                if was_sent:
                    n_sent += 1
        self.log_end({'n_sent_to_processing': n_sent})
