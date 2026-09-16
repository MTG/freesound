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

from donations.models import DonationRequest
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = "This command looks for DonationRequest objects older than a certain date and archives them by storing daily data as .csv files and removing from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            action="store",
            dest="retention_days",
            type=int,
            default=365 * 2,  # Default retention period is 2 years
            help="Number of days to retain donation requests before archiving",
        )

        parser.add_argument(
            "--folder",
            action="store",
            dest="folder",
            default=os.path.join(settings.ARCHIVED_DATA_PATH, "donation_requests"),
            help="Folder where to store archived donation requests data",
        )

        parser.add_argument(
            "--no-delete",
            action="store_true",
            dest="no_delete",
            help="Perform a dry run without actually deleting any donation requests",
        )

    def handle(self, **options):
        self.log_start()

        num_objects_archived = 0

        # Get number of DonationRequest objects older than the retention date
        retention_date = timezone.now() - datetime.timedelta(days=options["retention_days"])
        ddrr = DonationRequest.objects.filter(created__lt=retention_date).order_by("-created")

        if not ddrr.exists():
            console_logger.info("No donation requests older than the retention period were found.")
        else:
            # Iterate day be day from the oldest date of donation requests to the newest date (before the retention period)
            # Get rid of the time part by setting the time to midnight
            oldest_date = ddrr.last().created
            newest_date = ddrr.first().created
            oldest_date = oldest_date.replace(hour=0, minute=0, second=0, microsecond=0)
            newest_date = newest_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Iterate from oldest_date to newest_date by day
            current_date = oldest_date
            while current_date <= newest_date:
                next_date = current_date + datetime.timedelta(days=1)
                daily_ddrr = ddrr.filter(created__gte=current_date, created__lt=next_date).order_by("created")
                if daily_ddrr.exists():
                    folder = os.path.join(options["folder"], str(current_date.year))
                    os.makedirs(folder, exist_ok=True)
                    file_path = os.path.join(folder, f"donation_requests_{current_date.strftime('%Y-%m-%d')}.csv")
                    data_rows = []

                    # If file already exists, load existing data first
                    if os.path.exists(file_path):
                        with open(file_path, mode="r", newline="") as file:
                            reader = csv.reader(file)
                            next(reader)  # Skip header row
                            data_rows = [row for row in reader]

                    # Now compute new rows to be added to the existing data
                    data_rows_daily_ddr = [
                        [
                            str(donation_request.created),
                            donation_request.user_id,
                            donation_request.request_type,
                        ]
                        for donation_request in daily_ddrr
                    ]

                    # Add new rows to the existing data, but only if these rows are not already present
                    n_added = 0
                    for row in data_rows_daily_ddr:
                        if row not in data_rows:
                            data_rows.append(row)
                            n_added += 1

                    # Write the combined data back to the CSV file
                    console_logger.info(f"Writing {n_added} new rows to {file_path}")
                    with open(file_path, mode="w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["timestamp", "user_id", "request_type"])
                        writer.writerows(data_rows)

                    num_objects_archived += n_added
                    if not options["no_delete"]:
                        daily_ddrr.delete()
                current_date = next_date

        self.log_end({"num_objects_archived": num_objects_archived})
