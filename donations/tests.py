import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
import mock
import sounds.models
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

    def test_donation_form(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        data = {
            'amount': '0,1',
            'show_amount': True,
            'donation_type': '1',
        }
        ret = self.client.post("/donations/donate/", data)
        response =  ret.json()
        # Decimals must have '.' and not ','
        self.assertTrue('errors' in response)

        data['amount'] = '0.1'
        ret = self.client.post("/donations/donate/", data)
        response =  ret.json()
        # amount must be greater than 1
        self.assertTrue('errors' in response)

        data['amount'] = '5.1'
        ret = self.client.post("/donations/donate/", data)
        response =  ret.json()
        self.assertFalse('errors' in response)

    def test_donation_response(self):
        # 200 response on donate page
        resp = self.client.get(reverse('donate'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on donors page
        resp = self.client.get(reverse('donors'))
        self.assertEqual(resp.status_code, 200)

    def test_donation_emails(self):
        donation_settings, _ = donations.models.DonationsEmailSettings.objects.get_or_create()
        donation_settings.downloads_in_period = 1
        donation_settings.save()

        previous_date = datetime.datetime.now() - datetime.timedelta(days=500)
        self.user = User.objects.create_user(\
                username='jacob', email='j@test.com', password='top', id='46280')
        self.assertTrue(self.user.profile.last_donation_email_sent == None)

        donation = donations.models.Donation.objects\
                .create(user=self.user, amount=100, email=self.user.email, currency='EUR')
        donations.models.Donation.objects.filter(pk=donation.pk).update(created=previous_date)

        call_command('donations_mails')

        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.last_donation_email_sent != None)

        self.user2 = User.objects.create_user(\
                username='jacob2', email='j2@test.com', password='top2', id='46281')
        self.assertTrue(self.user2.profile.last_donation_email_sent == None)

        sounds.models.License.objects.create(
            name="New",
            abbreviation="n",
            summary="<p>",
            is_public=True,
            order=1,
            legal_code_url="http://creativecommons.org/licenses/sampling+/1.0/legalcode",
            deed_url="http://creativecommons.org/licenses/sampling+/1.0/"
        )
        for i in range(0, 5):
            sound = sounds.models.Sound.objects.create(
                user=self.user,
                original_filename="Test sound %i" % i,
                base_filename_slug="test_sound_%i" % i,
                license=sounds.models.License.objects.all()[0],
                md5="fakemd5_%i" % i)
            sounds.models.Download.objects.create(user=self.user2, sound=sound)

        call_command('donations_mails')
        self.user2.profile.refresh_from_db()
        self.assertTrue(self.user2.profile.last_donation_email_sent != None)

