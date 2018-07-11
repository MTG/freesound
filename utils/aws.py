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


def report_ses_stats():
    ses = init_client('ses')

    try:
        response = ses.get_send_statistics()
    except EndpointConnectionError as e:
        logger_console.error(e.message)
        return

    data = response['SendDataPoints']
    data.sort(key=lambda x: x['Timestamp'], reverse=True)

    size = settings.AWS_SES_BOUNCE_RATE_SAMPLE_SIZE
    total = 0
    complaints = 0
    bounces = 0

    for data_point in data:
        total += data_point['DeliveryAttempts']
        complaints += data_point['Complaints']
        bounces += data_point['Bounces']
        if size and total >= size:
            break

    bounce_rate = float(bounces) / total

    logger_web.info('Test email bounce rate {}'.format(json.dumps({'bounceRate': bounce_rate})))
    logger_web.info(json.dumps(data, default=str))

    return response
