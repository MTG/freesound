import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.core.urlresolvers import reverse
import mock
import donations.models
import views

class DonationTest(TestCase):

    def test_non_annon_donation_with_name(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        self.user = User.objects.create_user(\
                username='jacob', email='j@test.com', password='top', id='46280')
        # custom ={u'display_amount': True, u'user_id': 46280, u'campaign_id': 1, u'name': u'test'}
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJkaXNwbGF5X2Ftb3VudCI6IHRydWUsICJ1c2VyX2lkIjogNDYyODAsICJjYW1wYWlnbl9pZCI6IDEsICJuYW1lIjogInRlc3QifQ==',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, 'test')
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, True)

    def test_non_annon_donation(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        self.user = User.objects.create_user(\
                username='jacob', email='j@test.com', password='top', id='46280')
        # custom = {u'campaign_id': 1, u'user_id': 46280, u'display_amount': True}
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJkaXNwbGF5X2Ftb3VudCI6IHRydWUsICJ1c2VyX2lkIjogNDYyODAsICJjYW1wYWlnbl9pZCI6IDF9',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, None)
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, False)


    def test_annon_donation(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        # {u'campaign_id': 1, u'name': u'Anonymous', u'display_amount': True}
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJkaXNwbGF5X2Ftb3VudCI6IHRydWUsICJjYW1wYWlnbl9pZCI6IDEsICJuYW1lIjogIkFub255bW91cyJ9',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].is_anonymous, True)

