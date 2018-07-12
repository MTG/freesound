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
import json

import logging

logger_web = logging.getLogger('web')
logger_console = logging.getLogger('console')


class AwsCredentialsNotConfigured(Exception):
    message = 'AWS credentials are not configured'


def init_client(service):
    if not settings.AWS_REGION or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_SECRET_ACCESS_KEY:
        raise AwsCredentialsNotConfigured()

    return client(service, region_name=settings.AWS_REGION,
                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


class EmailStats(object):
    total = 0
    bounces = 0
    complaints = 0
    rejects = 0

    def _rate(self, value):
        return float(value) / self.total

    def render(self):
        return {
            'total': self.total,
            'bounces': self.bounces,
            'complaints': self.complaints,
            'rejects': self.rejects,
            'bounceRate': self._rate(self.bounces),
            'complaintRate': self._rate(self.complaints),
            'rejectRate': self._rate(self.rejects)
        }

    def aggregate(self, data):
        self.total += data['DeliveryAttempts']
        self.complaints += data['Complaints']
        self.bounces += data['Bounces']
        self.rejects += data['Rejects']


def report_ses_stats(sample_size=None, n_points=None):
    """Retrieves email statistics from AWS and sends the data to graylog"""
    ses = init_client('ses')

    try:
        response = ses.get_send_statistics()
    except EndpointConnectionError as e:
        logger_console.error(e.message)
        return

    data = response['SendDataPoints']
    data.sort(key=lambda x: x['Timestamp'], reverse=True)  # array of datapoints is not sorted originally

    try:
        sample_size = sample_size or settings.AWS_SES_BOUNCE_RATE_SAMPLE_SIZE
        n_points = n_points or settings.AWS_SES_SHORT_BOUNCE_RATE_DATAPOINTS
    except AttributeError:
        logger_console.error('AWS SES config variables not configured')
        return

    email_stats = EmailStats()
    count = 0
    result = {}

    for data_point in data:
        email_stats.aggregate(data_point)
        count += 1
        if count == n_points:
            result['shortTerm'] = email_stats.render()
        if sample_size and email_stats.total >= sample_size:
            break

    result['longTerm'] = email_stats.render()
    logger_web.info('AWS email stats: {}'.format(json.dumps(result)))

    return result
