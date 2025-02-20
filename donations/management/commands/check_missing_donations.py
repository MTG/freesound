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

import datetime
import logging
import requests
import json
from urllib.parse import parse_qs
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from donations.models import Donation, DonationCampaign
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger('commands')


class Command(LoggingBaseCommand):
    help = 'Synchronize Paypal donations'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--days',
            dest='days',
            default=1,
            type=int,
            help='Use this option to get the donations older than 1 day.')

    def handle(self, **options):
        self.log_start()

        days = options['days']
        n_donations_created = 0

        td = datetime.timedelta(days=days)
        start = timezone.now() - td

        one_day = datetime.timedelta(days=1)
        stop_date = timezone.now() - one_day
        params = {
            'METHOD': 'TransactionSearch',
            'STARTDATE': start,
            'ENDDATE': start + one_day,
            'VERSION': 94,
            'USER': settings.PAYPAL_USERNAME,
            'PWD': settings.PAYPAL_PASSWORD,
            'SIGNATURE': settings.PAYPAL_SIGNATURE
        }
        while stop_date >= start:
            req = requests.post(settings.PAYPAL_PAYMENTS_API_URL, data=params)
            raw_rsp = parse_qs(req.text)
            if raw_rsp['ACK'] == ['Success']:
                campaign = DonationCampaign.objects.order_by('date_start').last()
                Donation._meta.get_field('created').auto_now_add = False

                # Only consider 'Donation' and 'Payment' entries
                # TODO: explore the other types of entries like "transfer"
                max_range = len([key for key in raw_rsp.keys() if key.startswith("L_TYPE")])
                for i in range(max_range):
                    if raw_rsp['L_TYPE%d' % i][0] in ['Donation', 'Payment']:
                        amount = raw_rsp['L_AMT%d' % i][0]
                        if float(amount) < 0:
                            continue  # Don't create objects for donations with negative amounts
                        created_dt = datetime.datetime.strptime(raw_rsp['L_TIMESTAMP%d' % i][0], '%Y-%m-%dT%H:%M:%SZ')
                        donation_data = {
                            'email': raw_rsp['L_EMAIL%d' % i][0],
                            'display_name': 'Anonymous',
                            'amount': amount,
                            'currency': raw_rsp['L_CURRENCYCODE%d' % i][0],
                            'display_amount': False,
                            'is_anonymous': True,
                            'campaign': campaign,
                            'created': created_dt,
                            'source': 'p'
                        }
                        try:
                            user = User.objects.get(email=raw_rsp['L_EMAIL%d' % i][0])
                            donation_data['user'] = user
                        except User.DoesNotExist:
                            pass  # Don't link donation object to user object

                        obj, created = Donation.objects.get_or_create(
                                 transaction_id=raw_rsp['L_TRANSACTIONID%d'%i][0], defaults=donation_data)
                        if created:
                            n_donations_created += 1
                            del donation_data['campaign']
                            donation_data['created'] = raw_rsp['L_TIMESTAMP%d' % i][0]
                            if 'user' in donation_data:
                                donation_data['user'] = donation_data['user'].username  # Only log username in graylog
                            commands_logger.info(f'Created donation object ({json.dumps(donation_data)})')

            start = start + one_day
            params['STARTDATE'] = start
            params['ENDDATE'] = start + one_day

        self.log_end({'n_donation_objects_created': n_donations_created})
