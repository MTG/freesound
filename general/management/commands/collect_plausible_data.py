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

import requests
from django.conf import settings

from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger("console")


PLAUSIBLE_VISIST_PER_DAY_URL_TEMPLATE = "https://analytics.freesound.org/api/v1/stats/timeseries?site_id=freesound.org&metrics=visitors,pageviews,views_per_visit,bounce_rate,visit_duration&period=custom&date={start_date},{end_date}"
REQUESTS_TIMEOUT = 30


class Command(LoggingBaseCommand):
    help = "Collect data from Freesound Analytics (Plausible) so it is permanently stored"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            action="store",
            dest="folder",
            default=os.path.join(settings.ARCHIVED_DATA_PATH, "analytics"),
            help="Folder where to store archived plausible analytics data",
        )

        parser.add_argument(
            "--plausible-api-id",
            action="store",
            dest="plausible_api_id",
            default="PLAUSIBLE_KEY",
            help="Plausible API ID",
        )

    def handle(self, **options):
        self.log_start()

        folder = options["folder"]
        plausible_api_id = options["plausible_api_id"]

        os.makedirs(folder, exist_ok=True)

        # Find last plausible data stored
        plausible_filesnames_year = [
            (filename, filename.split("_")[2].split(".")[0])
            for filename in os.listdir(folder)
            if filename.startswith("plausible_analytics") and filename.endswith(".csv")
        ]
        last_year_file = max(plausible_filesnames_year, key=lambda x: x[1]) if plausible_filesnames_year else None
        if last_year_file is not None:
            last_year_file_data = list(csv.reader(open(os.path.join(folder, last_year_file[0]))))
            last_date_on_file = datetime.datetime(
                year=int(last_year_file_data[-1][0].split("/")[2]),
                month=int(last_year_file_data[-1][0].split("/")[1]),
                day=int(last_year_file_data[-1][0].split("/")[0]),
            )
            start_date = (last_date_on_file - datetime.timedelta(days=3)).strftime(
                "%Y-%m-%d"
            )  # Get 3 days back to get a slight overlap
        else:
            start_date = datetime.datetime(2021, 4, 16).strftime("%Y-%m-%d")

        # Now get all plausible data since that date until today
        end_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if start_date > end_date:
            raise Exception("Start date is after end date")
        url = PLAUSIBLE_VISIST_PER_DAY_URL_TEMPLATE.format(start_date=start_date, end_date=end_date)
        r = requests.get(url, headers={"Authorization": "Bearer {}".format(plausible_api_id)}, timeout=REQUESTS_TIMEOUT)

        try:
            response = r.json()
            data = response["results"]

            # Iterate over data and save a .csv file with all the data corresponding to each year
            # If a .csv file already exists for that year, append the new data to it (and overwrite existing data for the same day)
            # CSV file header should include properties date,visitors,pageviews,views_per_visit,visit_duration,bounce_rate
            data_by_year = {}
            for element in data:
                date_key = datetime.datetime(
                    year=int(element["date"].split("-")[0]),
                    month=int(element["date"].split("-")[1]),
                    day=int(element["date"].split("-")[2]),
                )
                year = date_key.year
                if year not in data_by_year:
                    data_by_year[year] = []
                data_by_year[year].append(
                    (
                        date_key,
                        int(element["visitors"]),
                        int(element["pageviews"]),
                        float(element["views_per_visit"] if element["views_per_visit"] is not None else 0),
                        float(element["visit_duration"] if element["visit_duration"] is not None else 0),
                        float(element["bounce_rate"] if element["bounce_rate"] is not None else 0),
                    )
                )

            for year, year_data in data_by_year.items():
                fpath = os.path.join(folder, f"plausible_analytics_{year}.csv")
                existing_data = []
                if os.path.exists(fpath):
                    existing_data = list(csv.reader(open(fpath)))
                    existing_data = [
                        (
                            datetime.datetime(
                                year=int(values[0].split("/")[2]),
                                month=int(values[0].split("/")[1]),
                                day=int(values[0].split("/")[0]),
                            ),
                            int(values[1].replace(",", "")),
                            int(values[2].replace(",", "")),
                            float(values[3].replace(",", "")),
                            float(values[4].replace(",", "")),
                            float(values[5].replace(",", "")),
                        )
                        for values in existing_data[1:]
                    ]
                all_data = {d.strftime("%d/%m/%Y"): (d, v1, v2, v3, v4, v5) for d, v1, v2, v3, v4, v5 in existing_data}
                for d, v1, v2, v3, v4, v5 in year_data:
                    all_data[d.strftime("%d/%m/%Y")] = (d, v1, v2, v3, v4, v5)
                all_data = sorted(all_data.values(), key=lambda x: x[0])
                data_write = "date,visitors,pageviews,views_per_visit,visit_duration,bounce_rate\n"
                data_write += "\n".join(
                    [
                        ",".join([values[0].strftime("%d/%m/%Y")] + list([str(e) for e in values[1:]]))
                        for values in all_data
                    ]
                )
                console_logger.info("Writing data to file: %s" % fpath)
                with open(fpath, "w") as fid:
                    fid.write(data_write)
        except Exception as e:
            # Print stacktrace
            import traceback

            console_logger.info("Failed getting visitors data from analystic: %s" % str(e))
            console_logger.info(traceback.format_exc())

        self.log_end()
