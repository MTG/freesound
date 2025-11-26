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

from django.conf import settings

from boto3 import client
from botocore.exceptions import EndpointConnectionError


class AwsCredentialsNotConfigured(Exception):
    message = "AWS credentials are not configured"


class AwsConnectionError(Exception):
    pass


def init_client(service):
    """
    Gets AWS credentials from config file and creates a client
    :param service: string that is passed to boto3.client
    :return: boto3.client object
    :raises: AwsCredentialsNotConfigured: missing or not filled in credentials in config file
    """
    if not settings.AWS_REGION or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_SECRET_ACCESS_KEY:
        raise AwsCredentialsNotConfigured()

    return client(
        service,
        region_name=settings.AWS_SQS_REGION,
        aws_access_key_id=settings.AWS_SQS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SQS_SECRET_ACCESS_KEY,
    )


class EmailStats:
    total = 0
    bounces = 0
    complaints = 0
    rejects = 0

    def _rate(self, value):
        return float(value) / self.total

    def render(self, prefix):
        return {
            prefix + "Total": self.total,
            prefix + "Bounces": self.bounces,
            prefix + "Complaints": self.complaints,
            prefix + "Rejects": self.rejects,
            prefix + "BounceRate": self._rate(self.bounces),
            prefix + "ComplaintRate": self._rate(self.complaints),
            prefix + "RejectRate": self._rate(self.rejects),
        }

    def aggregate(self, data):
        self.total += data["DeliveryAttempts"]
        self.complaints += data["Complaints"]
        self.bounces += data["Bounces"]
        self.rejects += data["Rejects"]


def get_ses_stats(sample_size, n_points):
    """
    Retrieves email statistics from AWS and sends the data to graylog
    :param sample_size: number of emails used to approximate long-term bounce rate from AWS SES dashboard
    :param n_points: number of DataSetPoints to calculate short-term bounce rate (for monitoring on finer scale)
    :return: dict with 'shortTerm' and 'longTerm' dicts that contain detailed info on bounces, complaints and rejects
    :raises AwsCredentialsNotConfigured: missing or not filled in credentials in config file
    :raises AwsConnectionError: connection problems with AWS server
    """
    ses = init_client("ses")

    try:
        response = ses.get_send_statistics()
    except EndpointConnectionError as e:
        raise AwsConnectionError(e)

    data = response["SendDataPoints"]
    data.sort(key=lambda x: x["Timestamp"], reverse=True)  # array of datapoints is not sorted originally

    email_stats = EmailStats()
    count = 0
    result = {}

    for data_point in data:
        email_stats.aggregate(data_point)
        count += 1
        if count == n_points:
            result.update(email_stats.render("shortTerm"))
        if sample_size and email_stats.total >= sample_size:
            break

    result.update(email_stats.render("longTerm"))

    return result
