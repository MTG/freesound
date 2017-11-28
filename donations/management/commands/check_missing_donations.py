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
from urlparse import parse_qs
from django.conf import settings
from donations.models import Donation, DonationCampaign
from django.core.management.base import BaseCommand

logger = logging.getLogger("web")


class Command(BaseCommand):
    help = 'Synchronize Paypal donations'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--days',
            action='store_true',
            dest='days',
            default=1,
            help='Use this option to get the donations older than 1 day.')

    def handle(self, **options):
        days = options['days']
        logger.info("Synchronizing donations from paypal")

        td = datetime.timedelta(days=days)
        start = datetime.datetime.now() - td

        one_day = datetime.timedelta(days=1)
        stop_date = datetime.datetime.now() - one_day
        params = {
            'METHOD': 'TransactionSearch',
            'STARTDATE': start,
            'ENDDATE': start + one_day,
            'VERSION': 94,
            'USER' : settings.PAYPAL_USERNAME,
            'PWD': settings.PAYPAL_PASSWORD,
            'SIGNATURE': settings.PAYPAL_SIGNATURE
        }
        while stop_date >= start:
            req = requests.post(settings.PAYPAL_PAYMENTS_API_URL, data=params)
            raw_rsp = parse_qs(req.text)
            if raw_rsp['ACK'] == ['Success']:
                campaign = DonationCampaign.objects.order_by('date_start').last()
                Donation._meta.get_field('created').auto_now_add = False
                for i in range(100):
                    if ('L_EMAIL%d' % i) in raw_rsp:
                        created = datetime.datetime.strptime(raw_rsp['L_TIMESTAMP%d' % i][0],'%Y-%m-%dT%H:%M:%SZ')
                        donation_data = {
                            'email': raw_rsp['L_EMAIL%d' % i][0],
                            'display_name': 'Anonymous',
                            'amount': raw_rsp['L_AMT%d' % i][0],
                            'currency': raw_rsp['L_CURRENCYCODE%d' % i][0],
                            'display_amount': False,
                            'is_anonymous': True,
                            'campaign': campaign,
                            'created': created,
                            'source': 'p'
                        }
                        obj, created = donations = Donation.objects.get_or_create(
                                 transaction_id=raw_rsp['L_TRANSACTIONID%d'%i][0], defaults=donation_data)
                        if created:
                            del donation_data['campaign']
                            donation_data['created'] = raw_rsp['L_TIMESTAMP%d' % i][0]
                            logger.info('Recevied donation (%s)' % json.dumps(donation_data))
                    else:
                        break

                    start = start + one_day
                    params['STARTDATE'] = start
                    params['ENDDATE'] = start + one_day
        logger.info("Synchronizing donations from paypal ended")
