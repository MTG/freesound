import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
import mock
import models
import views

class DonationTest(TestCase):

    def test_donation_complete(self):
        models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now())
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'Anonymous',
                'mc_currency': 'USD',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(models.Donation.objects.filter(\
                transaction_id='8B703020T00352816').exists(), True)

