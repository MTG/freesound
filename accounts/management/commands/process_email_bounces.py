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

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.db import IntegrityError
from accounts.models import EmailBounce
from boto3 import client
import json
import logging

logger = logging.getLogger('console')


class Command(BaseCommand):
    help = 'Retrieves email bounce info from AWS SQS and updates db'

    def handle(self, *args, **options):
        sqs = client('sqs', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        queue_url = settings.AWS_SQS_QUEUE_URL

        total = 0
        has_messages = True
        while has_messages:
            # Receive message from SQS queue
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=settings.AWS_SQS_MESSAGES_PER_CALL,
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )
            has_messages = len(response['Messages']) > 0

            for message in response['Messages']:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])

                data = json.loads(body['Message'])
                if data['notificationType'] == 'Bounce':
                    bounce_data = data['bounce']
                    bounce_type = EmailBounce.type_from_string(bounce_data['bounceType'])
                    timestamp = parse_datetime(bounce_data['timestamp'])

                    for recipient in bounce_data['bouncedRecipients']:
                        email = recipient['emailAddress']
                        try:
                            user = User.objects.get(email__iexact=email)
                            EmailBounce.objects.create(user=user, type=bounce_type, timestamp=timestamp)
                        except User.DoesNotExist:
                            logger.info('User {} not found in database')  # user probably got deleted
                        except IntegrityError:  # message duplicated
                            pass

                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=receipt_handle
                    )
                    total += 1

        logger.info('Processed {} messages from queue'.format(total))
