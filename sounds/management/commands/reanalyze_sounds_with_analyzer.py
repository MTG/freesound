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

from django.utils import timezone

from sounds.models import SoundAnalysis
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """This script sends "--limit" sounds to re-analyze with the specified analyzer if the sounds were last analyzed before the cutoff date.
    It can be used to re-analyze all sounds with a given analyzer if the analyer has been updated (but the name is the same), and we don't want to
    send all sounds to the re-anayze queue as the queue will be blocked. Setting up a cronjob with this command, we can keep on sending sounds to the queue
    in small batches, and with the cutoff date set to the date in which the analyzer was updated, we can make sure that only sounds that were analyzed before 
    the update are sent to the queue. When the command returns n_sent_to_reanalyze=0, then the cronjob can be stopped as all sounds have been sent to the queue 
    for re-analysis.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "analyzer_name",
            action="store",
            help="Name of the analyzer with which to analyze the sounds.",
        )

        parser.add_argument(
            "cutoff_date",
            action="store",
            help="Cutoff date for re-analyzing sounds, with date included (format: YYYY-MM-DD).",
        )

        parser.add_argument(
            "--limit",
            action="store",
            dest="limit",
            default=1000,
            type=int,
            help="Limit the number of sounds to process (default: 1000).",
        )

    def handle(self, *args, **options):
        self.log_start()
        analyzer_name = options["analyzer_name"]
        cutoff_date = options["cutoff_date"]
        cutoff_date_datetime = timezone.datetime.strptime(cutoff_date, "%Y-%m-%d")
        cutoff_date_datetime = timezone.make_aware(cutoff_date_datetime, timezone.get_current_timezone())
        cutoff_date_datetime = cutoff_date_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
        console_logger.info(f"Cutoff date: {cutoff_date}")
        limit = options["limit"]

        qs = SoundAnalysis.objects.filter(
            analyzer=analyzer_name, last_analyzer_finished__lte=cutoff_date_datetime, analysis_status="OK"
        )
        total_matching_cutoff_date = qs.count()
        qs = qs[:limit]
        console_logger.info(
            f"Found {total_matching_cutoff_date} sounds being analyzed before the cutoff date {cutoff_date}. Will send {qs.count()} sounds with analyzer '{analyzer_name}' to re-analyze."
        )
        for sa in qs:
            sa.re_run_analysis()

        self.log_end(
            {
                "analyzer_name": analyzer_name,
                "cutoff_date": cutoff_date,
                "limit": limit,
                "n_sent_to_reanalyze": total_matching_cutoff_date,
            }
        )
