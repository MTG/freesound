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
import time

import requests
from django.conf import settings

from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger("console")


GRAYLOG_API_BASE_URL = "https://graylog.freesound.org/api/"
PLAUSIBLE_VISIST_PER_DAY_URL_TEMPLATE = "https://analytics.freesound.org/api/v1/stats/timeseries?site_id=freesound.org&period=custom&date={start_date},{end_date}"
REQUESTS_TIMEOUT = 30


def build_query_url(query, fields, date_from, date_to, page_size, offset=0):
    return (
        GRAYLOG_API_BASE_URL
        + "search/universal/absolute?query={query}&fields={fields}&from={from}&to={to}&limit={limit}&offset={offset}".format(
            **{
                "query": query,
                "fields": fields,
                "limit": page_size,
                "offset": offset,
                "from": (date_from - datetime.timedelta(hours=2)).strftime("%Y-%m-%d+%H:%M:%S"),
                "to": (date_to - datetime.timedelta(hours=2)).strftime("%Y-%m-%d+%H:%M:%S"),
            }
        )
    )


def request_popup_messages(date_from, date_to, page_size, graylog_username, graylog_password):
    def get_messages(url):
        r = requests.get(
            url,
            auth=(graylog_username, graylog_password),
            headers={"Accept": "application/json"},
            timeout=REQUESTS_TIMEOUT,
        )
        response = r.json()
        if "total_results" not in response:
            return -1, list()
        return response["total_results"], [
            (m["message"]["timestamp"], m["message"].get("user_id", None)) for m in response["messages"]
        ]

    query = '"Showing after download donate modal"'
    fields = "user_id"
    url = build_query_url(query, fields, date_from, date_to, page_size)
    total_results, messages = get_messages(url)
    page = 1
    console_logger.info("Getting popup messages for %s (%i)" % (date_from.strftime("%Y-%m-%d"), total_results))
    while len(messages) < total_results and total_results != -1:
        url = build_query_url(query, fields, date_from, date_to, page_size, offset=page * page_size)
        total_results, new_messages = get_messages(url)
        messages += new_messages
        page += 1
        time.sleep(2)  # Do some sleep to not collapse logserver while issuing responses

    return messages


def request_email_messages(date_from, date_to, page_size, graylog_username, graylog_password):
    def get_messages(url):
        r = requests.get(
            url,
            auth=(graylog_username, graylog_password),
            headers={"Accept": "application/json"},
            timeout=REQUESTS_TIMEOUT,
        )
        response = r.json()
        if "total_results" not in response:
            return -1, list()
        return response["total_results"], [
            (
                m["message"]["timestamp"],
                m["message"].get("user_id", None),
                m["message"].get("donation_email_type", None),
            )
            for m in response["messages"]
        ]

    query = '"Sent donation email"'
    fields = "user_id,donation_email_type"
    url = build_query_url(query, fields, date_from, date_to, page_size)
    total_results, messages = get_messages(url)
    page = 1
    console_logger.info("Getting email messages for %s (%i)" % (date_from.strftime("%Y-%m-%d"), total_results))
    while len(messages) < total_results and total_results != -1:
        url = build_query_url(query, fields, date_from, date_to, page_size, offset=page * page_size)
        total_results, new_messages = get_messages(url)
        messages += new_messages
        page += 1
        time.sleep(2)  # Do some sleep to not collapse logserver while issuing responses

    return messages


def request_donations_messages(date_from, date_to, page_size, graylog_username, graylog_password):
    def get_messages(url):
        r = requests.get(
            url,
            auth=(graylog_username, graylog_password),
            headers={"Accept": "application/json"},
            timeout=REQUESTS_TIMEOUT,
        )
        response = r.json()
        if "total_results" not in response:
            return -1, list()
        return response["total_results"], [
            (
                m["message"]["timestamp"],
                m["message"].get("user_id", None),
                float(m["message"].get("amount", 0)),
                m["message"].get("currency", None),
                m["message"].get("donation_source", None),
            )
            for m in response["messages"]
        ]

    query = '"Received donation"'
    fields = "user_id,amount,currency,donation_source"
    url = build_query_url(query, fields, date_from, date_to, page_size)
    total_results, messages = get_messages(url)
    page = 1
    console_logger.info("Getting donations messages for %s (%i)" % (date_from.strftime("%Y-%m-%d"), total_results))
    while len(messages) < total_results and total_results != -1:
        url = build_query_url(query, fields, date_from, date_to, page_size, offset=page * page_size)
        total_results, new_messages = get_messages(url)
        messages += new_messages
        page += 1
        time.sleep(2)  # Do some sleep to not collapse logserver while issuing responses

    return messages


class Command(LoggingBaseCommand):
    help = "Synchronize Paypal donations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            action="store",
            dest="folder",
            default=os.path.join(settings.DATA_PATH, "donations_collected_data"),
            help="Folder where to store collected donations data",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            dest="overwrite",
            default=False,
            help="Whether to overwrite existing files with new data (if not set, it will only get data for dates that do not have files yet)",
        )
        parser.add_argument(
            "--page_size",
            action="store",
            dest="page_size",
            type=int,
            default=5000,
            help="Number of results to fetch per page",
        )
        parser.add_argument(
            "--graylog-api-username",
            action="store",
            dest="graylog_api_username",
            default="apiuser",
            help="Graylog API username",
        )
        parser.add_argument(
            "--graylog-api-password",
            action="store",
            dest="graylog_api_password",
            default="sp9-D8w-zSc-dWC",
            help="Graylog API password",
        )
        parser.add_argument(
            "--plausible-api-id",
            action="store",
            dest="plausible_api_id",
            default="Yjjjif6hJQ-LE8uYSWWI4NdCwz1WXC2_rPmm4D85Pi-rc4IELoZ_nfgoimJP1ljH",
            help="Plausible API ID",
        )

    def handle(self, **options):
        self.log_start()

        data_path = options["folder"]
        overwrite_existing = options["overwrite"]
        page_size = options["page_size"]
        graylog_username = options["graylog_api_username"]
        graylog_password = options["graylog_api_password"]
        plausible_api_id = options["plausible_api_id"]

        start_date = datetime.date(2017, 7, 11)  # Start collecting data from the moment we started donations campaign
        current_date = start_date
        while current_date <= datetime.date.today():
            date_from = current_date - datetime.timedelta(days=1)
            current_year_label = str(date_from.year)
            date_to = current_date
            date_label = date_from.strftime("%Y-%m-%d")

            # Get popup messages information
            filename = date_label + "_popups.csv"
            filepath = os.path.join(data_path, current_year_label, filename)
            if not os.path.exists(os.path.dirname(filepath)):
                os.mkdir(os.path.dirname(filepath))
            if not os.path.exists(filepath) or overwrite_existing:
                # If file does not exist, get data and save it
                data = request_popup_messages(date_from, date_to, page_size, graylog_username, graylog_password)
                with open(filepath, "w") as csvfile:
                    writer = csv.writer(
                        csvfile,
                        delimiter="\t",
                    )
                    writer.writerow(["timestamp", "user_id"])
                    writer.writerows(data)

            # Get email data
            filename = date_label + "_emails.csv"
            filepath = os.path.join(data_path, current_year_label, filename)
            if not os.path.exists(os.path.dirname(filepath)):
                os.mkdir(os.path.dirname(filepath))
            if not os.path.exists(filepath) or overwrite_existing:
                # If file does not exist, get data and save it
                data = request_email_messages(date_from, date_to, page_size, graylog_username, graylog_password)
                with open(filepath, "w") as csvfile:
                    writer = csv.writer(
                        csvfile,
                        delimiter="\t",
                    )
                    writer.writerow(["timestamp", "user_id", "donation_email_type"])
                    writer.writerows(data)

            # Get donations data
            filename = date_label + "_donations.csv"
            filepath = os.path.join(data_path, current_year_label, filename)
            if not os.path.exists(os.path.dirname(filepath)):
                os.mkdir(os.path.dirname(filepath))
            if not os.path.exists(filepath) or overwrite_existing:
                # If file does not exist, get data and save it
                data = request_donations_messages(date_from, date_to, page_size, graylog_username, graylog_password)
                with open(filepath, "w") as csvfile:
                    writer = csv.writer(
                        csvfile,
                        delimiter="\t",
                    )
                    writer.writerow(["timestamp", "user_id", "amount", "currency", "donation_source"])
                    writer.writerows(data)

            current_date += datetime.timedelta(days=1)
        console_logger.info(
            "Finished collecting data from log server. Last info from date: {}".format(
                (current_date - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
            )
        )

        # Collect plausible analytics data

        fpath = os.path.join(data_path, "visitors_data.csv")
        try:
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
                    int(values[3].replace(",", "")),
                    float(values[4].replace(",", "")),
                )
                for values in existing_data[1:]
            ]  # Skip header row
            dates = [date for date, _, _, _, _ in existing_data]
            dates = sorted(dates)
            last_date = dates[-1]
        except (IOError, IndexError):
            existing_data = []
            last_date = datetime.datetime(2017, 1, 6)

        existing_date_keys = [d.strftime("%d/%m/%Y") for d, _, _, _, _ in existing_data]
        start_date = last_date.strftime("%Y-%m-%d")
        end_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        url = PLAUSIBLE_VISIST_PER_DAY_URL_TEMPLATE.format(start_date=start_date, end_date=end_date)
        r = requests.get(url, headers={"Authorization": "Bearer {}".format(plausible_api_id)}, timeout=REQUESTS_TIMEOUT)

        try:
            response = r.json()
            data_list = []
            if "results" in response:
                for element in response["results"]:
                    date_key = datetime.datetime(
                        year=int(element["date"].split("-")[0]),
                        month=int(element["date"].split("-")[1]),
                        day=int(element["date"].split("-")[2]),
                    )
                    if date_key.strftime("%d/%m/%Y") not in existing_date_keys:
                        data_list.append((date_key, int(element["visitors"]), 0, 0, 0.0))

            all_data = data_list + existing_data
            all_data = sorted(all_data, key=lambda x: x[0])

            data_write = "Date,users,newUsers,sessions,avgPageLoadTime\n"
            data_write += "\n".join(
                [",".join([values[0].strftime("%d/%m/%Y")] + list([str(e) for e in values[1:]])) for values in all_data]
            )
            fid = open(fpath, "w")
            fid.write(data_write)
            fid.close()
            console_logger.info("Got visitors data for %i days" % len(all_data))
        except Exception as e:
            console_logger.info("Failed getting visitors data from analystic: %s" % str(e))

        self.log_end()
