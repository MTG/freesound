import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.core.urlresolvers import reverse
import mock
import donations.models
import views

class DonationTest(TestCase):

    def test_non_annon_donation(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now())
        self.user = User.objects.create_user(\
                username='jacob', email='j@test.com', password='top', id='46280')
        # custom = {u'campaign_id': 1, u'name': None, u'user_id': 46280}
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJ1c2VyX2lkIjogNDYyODAsICJuYW1lIjogbnVsbCwgImNhbXBhaWduX2lkIjogMX0=',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816').exists(), True)

    def test_annon_donation(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        # {u'campaign_id': 1, u'name': u'Anonymous'}
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJuYW1lIjogIkFub255bW91cyIsICJjYW1wYWlnbl9pZCI6IDF9',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816').exists(), True)

