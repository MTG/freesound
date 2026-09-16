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

import csv
import datetime
import logging
import os

from django.conf import settings
from django.utils import timezone

from search.models import SearchQuery
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = "This command looks for SearchQuery objects older than a certain date and archives them by storing daily data as .csv files and removing from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            action="store",
            dest="retention_days",
            type=int,
            default=365 * 2,  # Default retention period is 2 years
            help="Number of days to retain search queries before archiving",
        )

        parser.add_argument(
            "--folder",
            action="store",
            dest="folder",
            default=os.path.join(settings.ARCHIVED_DATA_PATH, "search_queries"),
            help="Folder where to store archived search queries data",
        )

        parser.add_argument(
            "--no-delete",
            action="store_true",
            dest="no_delete",
            help="Perform a dry run without actually deleting any search queries",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            dest="overwrite",
            help="Overwrite existing archived files if they already exist",
        )

    def handle(self, **options):
        self.log_start()

        num_objects_archived = 0

        # Get number of SearchQuery objects older than the retention date
        retention_date = timezone.now() - datetime.timedelta(days=options["retention_days"])
        sqs = SearchQuery.objects.filter(created__lt=retention_date).order_by("-created")

        if not sqs.exists():
            console_logger.info("No search queries older than the retention period were found.")
        else:
            # Iterate day be day from the oldest date of search queries to the newest date (before the retention period)
            # Get rid of the time part by setting the time to midnight
            oldest_date = sqs.last().created
            newest_date = sqs.first().created
            oldest_date = oldest_date.replace(hour=0, minute=0, second=0, microsecond=0)
            newest_date = newest_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Iterate from oldest_date to newest_date by day
            current_date = oldest_date
            while current_date <= newest_date:
                next_date = current_date + datetime.timedelta(days=1)
                daily_sqs = sqs.filter(created__gte=current_date, created__lt=next_date)
                if daily_sqs.exists():
                    folder = os.path.join(options["folder"], str(current_date.year))
                    os.makedirs(folder, exist_ok=True)
                    file_path = os.path.join(folder, f"search_queries_{current_date.strftime('%Y-%m-%d')}.csv")
                    if not os.path.exists(file_path) or options["overwrite"]:
                        with open(file_path, mode="w", newline="") as file:
                            writer = csv.writer(file)
                            writer.writerow(["timestamp", "user_id", "ip", "query", "query_time", "num_results", "url"])
                            for search_query in daily_sqs:
                                writer.writerow(
                                    [
                                        str(search_query.created),
                                        search_query.user_id,
                                        search_query.data.get("ip", ""),
                                        search_query.query,
                                        search_query.data.get("query_time", -1),
                                        search_query.data.get("num_results", -1),
                                        search_query.data.get("url", ""),
                                    ]
                                )
                    num_objects_archived += daily_sqs.count()
                    if not options["no_delete"]:
                        daily_sqs.delete()
                current_date = next_date

        self.log_end({"num_objects_archived": num_objects_archived})
