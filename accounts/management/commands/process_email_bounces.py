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
from utils.filesystem import create_directories
from boto3 import client
from botocore.exceptions import EndpointConnectionError
import json
import logging
import time
import os

logger_web = logging.getLogger('web')
logger_console = logging.getLogger('console')


def create_dump_file():
    path = os.path.join(settings.DATA_PATH, 'bounced_emails')
    create_directories(path)
    return os.path.join(path, time.strftime('%Y%m%d_%H%M') + '.json')


def decode_idna_email(email):
    """Takes email (unicode) with IDNA encoded domain and returns true unicode representation"""
    user, domain = email.split('@')
    domain = domain.encode().decode('idna')  # explicit encode to bytestring for python 2/3 compatability
    return user + '@' + domain


class Command(BaseCommand):
    help = 'Retrieves email bounce info from AWS SQS and updates db.'
    # At the time of implementation AWS has two queue types: standard and FIFO. Standard queue will not guarantee the
    # uniqueness of messages that we are receiving, thus it is possible to get duplicates of the same message.
    # Configuration parameter AWS_SQS_MESSAGES_PER_CALL can take values from 1 to 10 and indicates number of messages
    # returned by AWS. By setting it to 1 you guarantee no duplicates, but the speed is slower. By setting it to 10 you
    # can speed up the process, but there will be redundancy in the received data, thus among 10 messages received there
    # might be only 4~5 unique ones. FIFO queues don't have the duplication issue, but the messages are delivered in
    # FIFO manner.

    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            dest='save',
            default=False,
            help="Save all bounce messages on disk",
        )

        parser.add_argument(
            '--no-delete',
            action='store_true',
            dest='no_delete',
            default=False,
            help="Don't delete messages from queue",
        )

    def handle(self, *args, **options):
        if not settings.AWS_REGION or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_SECRET_ACCESS_KEY:
            logger_console.error('AWS credentials are not configured')
            return

        queue_url = settings.AWS_SQS_QUEUE_URL
        if not queue_url:
            logger_console.error('AWS queue URL is not configured')
            return

        messages_per_call = settings.AWS_SQS_MESSAGES_PER_CALL
        if not 1 <= settings.AWS_SQS_MESSAGES_PER_CALL <= 10:
            logger_console.warn('Invalid value for number messages to process per call: {}, using 1'.format(messages_per_call))
            messages_per_call = 1

        save_messages = options['save']
        no_delete = options['no_delete']
        if no_delete:
            logger_console.info('Running without deleting messages from queue (one batch)')

        sqs = client('sqs', region_name=settings.AWS_REGION,
                     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        total_messages = 0
        total_bounces = 0  # counts multiple recipients of the same mail
        has_messages = True
        all_messages = []

        while has_messages:
            # Receive message from SQS queue
            try:
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=messages_per_call,
                    VisibilityTimeout=0,
                    WaitTimeSeconds=0
                )
            except EndpointConnectionError as e:
                logger_console.error(e.message)
                return
                
            messages = response.get('Messages', [])
            has_messages = not no_delete and len(messages) > 0

            for message in messages:
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                data = json.loads(body['Message'])

                if data['notificationType'] == 'Bounce':
                    bounce_data = data['bounce']
                    bounce_type = EmailBounce.type_from_string(bounce_data['bounceType'])
                    timestamp = parse_datetime(bounce_data['timestamp'])
                    is_duplicate = False

                    for recipient in bounce_data['bouncedRecipients']:
                        email = decode_idna_email(recipient['emailAddress'])
                        try:
                            user = User.objects.get(email__iexact=email)
                            EmailBounce.objects.create(user=user, type=bounce_type, timestamp=timestamp)
                            total_bounces += 1
                        except User.DoesNotExist:  # user probably got deleted
                            logger_console.info(u'User {} not found in database (probably deleted)'.format(email))
                        except IntegrityError:  # message duplicated
                            is_duplicate = True

                    if not no_delete:
                        sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=receipt_handle
                        )

                    if not is_duplicate:
                        total_messages += 1
                        if save_messages:
                            all_messages.append(data)

        if save_messages:
            filename = create_dump_file()
            with open(filename, 'w') as fp:
                json.dump(all_messages, fp)

        result = {'nMailsBounced': total_messages, 'nBounces': total_bounces}
        logger_web.info('Finished processing messages from queue ({})'.format(json.dumps(result)))
