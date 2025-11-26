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

from django.conf import settings
from django.core.management.base import BaseCommand

from utils.aws import AwsCredentialsNotConfigured, EndpointConnectionError, get_ses_stats

console_logger = logging.getLogger("console")
commands_logger = logging.getLogger("commands")


class Command(BaseCommand):
    help = "Retrieves email stats from AWS SES and reports it to graylog."

    def add_arguments(self, parser):
        parser.add_argument(
            "--short-term-datapoints",
            type=int,
            dest="n_datapoints",
            help="Number of datapoints to aggregate for short-term stats (cronjob interval / aws interval (15mins))",
        )

        parser.add_argument(
            "--long-term-sample-size",
            type=int,
            dest="sample_size",
            help="Number of emails to approximate bounce rate from AWS dashboard",
        )

    def handle(self, *args, **options):
        try:
            sample_size = options["sample_size"] or settings.AWS_SES_BOUNCE_RATE_SAMPLE_SIZE
            n_points = options["n_datapoints"] or settings.AWS_SES_SHORT_BOUNCE_RATE_DATAPOINTS
        except AttributeError:
            console_logger.info("AWS SES config variables not configured")
            return

        try:
            stats = get_ses_stats(sample_size, n_points)
        except (AwsCredentialsNotConfigured, EndpointConnectionError) as e:
            console_logger.info(str(e))
            return

        commands_logger.info(f"Reporting AWS email stats ({json.dumps(stats)})")
        console_logger.info(f"Reporting AWS email stats ({json.dumps(stats)})")
