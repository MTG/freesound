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
import re
from urllib.parse import parse_qsl, urlparse

from django.conf import settings
from django.core.cache import caches
from django.utils import timezone

from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger("console")

cache_search_queries = caches["search_queries"]


class Command(LoggingBaseCommand):
    help = (
        'This command looks for search query logs in the search_query redis store and saves them in "archived" csv files. '
        "It also deletes archived files that are older than the specified retention period."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-hours",
            action="store",
            dest="retention_hours",
            type=int,
            default=2,  # Default retention period is 2 hours
            help="Number of hours to retain search queries in the cache before archiving",
        )

        parser.add_argument(
            "--archive-files-retention-days",
            action="store",
            dest="archive_files_retention_days",
            type=int,
            default=None,  # By default we don't delete any archive files
            help="Number of days to retain search queries archived documents before finally deleting them",
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
        num_files_deleted = 0

        # Get all existing logs in the search_query cache
        retention_date = timezone.now() - datetime.timedelta(hours=options["retention_hours"])
        elements_to_archive = []
        for key in cache_search_queries._cache.get_client().scan_iter("*"):
            key = key.decode("utf-8").split(":")[-1]
            element = cache_search_queries.get(key)
            element["key"] = key
            # element has a 'timestamp' property in isoformat, so it can be compared as string
            if element["timestamp"] < retention_date.isoformat():
                elements_to_archive.append(element)

        if not elements_to_archive:
            console_logger.info("No search queries older than the retention period were found.")
        else:
            elements_to_archive.sort(key=lambda x: x["timestamp"])

            # Process every element to archive so that the 'url' field is parsed and split into a
            # 'path' property and 'params' property for easier analysis later
            for element in elements_to_archive:
                url_parts = urlparse(element["url"])
                element["path"] = url_parts.path
                element["params"] = dict(parse_qsl(url_parts.query))

            # Save the elements to archive into a CSV file(s)
            # Files should be named like "folder/YYYY/search_queries_YYYY-MM-DD.csv"
            # If there are elements for a file that already exists, they should be appended unless the --overwrite option is specified

            # Group elements by date
            # Also keep a list of all the keys in the "params" property by date as this will be used to later define CSV coluns
            elements_by_date = {}
            params_keys_by_date = {}
            for element in elements_to_archive:
                date = element["timestamp"][:10]  # Get the date part (YYYY-MM-DD)
                if date not in elements_by_date:
                    elements_by_date[date] = []
                    params_keys_by_date[date] = set()

                # Now modify the timestamp because we already grouped by date, and we only want the time hh:mm:ss.microseconds part
                # We can also skip the last timezone offset part (+00:00)
                element["timestamp"] = element["timestamp"][11:-6]

                elements_by_date[date].append(element)
                params_keys_by_date[date].update(element["params"].keys())  # Collect all param keys for the date

            # Save the grouped elements into CSV files
            basic_fieldnames = ["timestamp", "path", "user_id", "query_time", "num_results"]
            for date, elements in elements_by_date.items():
                year = date[:4]
                year_dir = os.path.join(options["folder"], year)
                os.makedirs(year_dir, exist_ok=True)
                file_path = os.path.join(year_dir, f"search_queries_{date}.csv")
                file_exists = os.path.isfile(file_path)
                if file_exists and not options["overwrite"]:
                    # If file exists, load data from the file, combine with new data and re-write the file
                    # This is important because new entries for that file might have new parameter keys that need to be included in the CSV columns
                    # We also need therefore to list the parameter keys for the existing file and combine them with the new ones
                    with open(file_path, "r", newline="") as csvfile:
                        reader = csv.DictReader(csvfile)
                        existing_fieldnames = reader.fieldnames if reader.fieldnames else []
                        existing_param_keys = set(existing_fieldnames) - set(basic_fieldnames)
                        params_keys_by_date[date].update(existing_param_keys)
                        existing_rows = list(reader)
                    # Remove entries from "elements" which are also present in existing_rows to avoid duplicates
                    existing_keys = {row["timestamp"] for row in existing_rows if "timestamp" in row}
                    elements = [element for element in elements if element["timestamp"] not in existing_keys]
                else:
                    existing_rows = []

                with open(file_path, "w", newline="") as csvfile:
                    fieldnames = basic_fieldnames + sorted(params_keys_by_date[date])
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in existing_rows:
                        writer.writerow(row)
                    for element in elements:
                        row = {field: str(element.get(field, "")) for field in basic_fieldnames}
                        for param_key in params_keys_by_date[date]:
                            row[param_key] = str(element["params"].get(param_key, ""))
                        writer.writerow(row)
                num_objects_archived += len(elements)

            # Now delete these keys from cache
            if not options["no_delete"]:
                for element in elements_to_archive:
                    cache_key = element["key"]
                    cache_search_queries.delete(cache_key)

        # Now delete the old files in the archive which are older than the archive retention period
        if options["archive_files_retention_days"] is not None:
            num_files_deleted = self.delete_old_archive_files(
                options["archive_files_retention_days"], options["folder"], options["no_delete"]
            )

        self.log_end({"num_objects_archived": num_objects_archived, "num_archive_files_deleted": num_files_deleted})

    def delete_old_archive_files(self, archive_files_retention_days, folder, no_delete):
        num_files_deleted = 0
        if not os.path.isdir(folder):
            return num_files_deleted

        retention_cutoff_date = (timezone.now() - datetime.timedelta(days=archive_files_retention_days)).date()
        filename_re = re.compile(r"^search_queries_(\d{4}-\d{2}-\d{2})\.csv$")
        for year_dir_name in sorted(os.listdir(folder)):
            year_dir_path = os.path.join(folder, year_dir_name)
            if not os.path.isdir(year_dir_path):
                continue
            for filename in sorted(os.listdir(year_dir_path)):
                match = filename_re.match(filename)
                if not match:
                    continue
                file_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
                if file_date < retention_cutoff_date:
                    file_path = os.path.join(year_dir_path, filename)
                    console_logger.info(f"Deleting expired search queries archive file {file_path}")
                    if not no_delete:
                        os.remove(file_path)
                    num_files_deleted += 1
            if not no_delete and not os.listdir(year_dir_path):
                os.rmdir(year_dir_path)

        return num_files_deleted
