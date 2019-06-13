import datetime

import mock
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

import donations.models
import sounds.models
from accounts.models import EmailPreferenceType, UserEmailSetting
from sounds.models import License


class DonationTest(TestCase):

    fixtures = ['licenses', 'email_preference_type']

    def test_non_annon_donation_with_name_paypal(self):
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
            resp = self.client.post(reverse('donation-complete-paypal'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, 'test')
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, True)
            self.assertEqual(donations_query[0].source, 'p')

    def test_non_annon_donation_paypal(self):
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
            resp = self.client.post(reverse('donation-complete-paypal'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, None)
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, False)
            self.assertEqual(donations_query[0].source, 'p')


    def test_annon_donation_paypal(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)

        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'eyJkaXNwbGF5X2Ftb3VudCI6IHRydWUsICJjYW1wYWlnbl9pZCI6IDEsICJuYW1lIjogIkFub255bW91cyJ9',
                'mc_currency': 'EUR',
                'mc_gross': '1.00'}

        with mock.patch('donations.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete-paypal'), params)
            self.assertEqual(resp.status_code, 200)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].is_anonymous, True)
            self.assertEqual(donations_query[0].source, 'p')

    def test_non_annon_donation_with_name_stripe(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        self.user = User.objects.create_user(\
                username='fsuser', email='j@test.com', password='top', id='46280')
        self.client.login(username='fsuser', password='top')
        # custom ={u'display_amount': True, u'user_id': 46280, u'campaign_id': 1, u'name': u'test'}
        params = {
                'stripeToken': '8B703020T00352816',
                'stripeEmail': 'donor@freesound.org',
                'amount': '1.5',
                'show_amount': True,
                'donation_type': '2',
                'name_option': 'test'
        }
        with mock.patch('stripe.Charge.create') as mock_create:
            mock_create.return_value = {'status': 'succeeded', 'id': 'txn123'}
            resp = self.client.post(reverse('donation-complete-stripe'), params)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='txn123')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, 'test')
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, True)
            self.assertEqual(donations_query[0].source, 's')

    def test_non_annon_donation_stripe(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        self.user = User.objects.create_user(\
                username='fsuser', email='j@test.com', password='top', id='46280')
        self.client.login(username='fsuser', password='top')
        # custom = {u'campaign_id': 1, u'user_id': 46280, u'display_amount': True}
        params = {
                'stripeToken': '8B703020T00352816',
                'stripeEmail': 'donor@freesound.org',
                'amount': '1.5',
                'show_amount': True,
                'donation_type': '0'
            }

        with mock.patch('stripe.Charge.create') as mock_create:
            mock_create.return_value = {'status': 'succeeded', 'id': 'txn123'}
            resp = self.client.post(reverse('donation-complete-stripe'), params)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='txn123')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].campaign_id, 1)
            self.assertEqual(donations_query[0].display_name, None)
            self.assertEqual(donations_query[0].user_id, 46280)
            self.assertEqual(donations_query[0].is_anonymous, False)
            self.assertEqual(donations_query[0].source, 's')

    def test_annon_donation_stripe(self):
        donations.models.DonationCampaign.objects.create(\
                goal=200, date_start=datetime.datetime.now(), id=1)
        # {u'campaign_id': 1, u'name': u'Anonymous', u'display_amount': True}
        params = {
                'stripeToken': '8B703020T00352816',
                'stripeEmail': 'donor@freesound.org',
                'amount': '1.5',
                'show_amount': True,
                'donation_type': '1'
            }

        with mock.patch('stripe.Charge.create') as mock_create:
            mock_create.return_value = {'status': 'succeeded', 'id': 'txn123'}
            resp = self.client.post(reverse('donation-complete-stripe'), params)
            donations_query = donations.models.Donation.objects.filter(\
                transaction_id='txn123')
            self.assertEqual(donations_query.exists(), True)
            self.assertEqual(donations_query[0].is_anonymous, True)
            self.assertEqual(donations_query[0].source, 's')

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

        long_mail = ('1'*256) + '@freesound.org'
        data['name_option'] = long_mail
        data['donation_type'] = '2'
        ret = self.client.post("/donations/donate/", data)
        response =  ret.json()
        self.assertTrue('errors' in response)

    def test_donation_response(self):
        # 200 response on donate page
        resp = self.client.get(reverse('donate'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on donors page
        resp = self.client.get(reverse('donors'))
        self.assertEqual(resp.status_code, 200)

    def test_donation_emails(self):
        donation_settings, _ = donations.models.DonationsEmailSettings.objects.get_or_create()
        TEST_DOWNLOADS_IN_PERIOD = 1
        donation_settings.downloads_in_period = TEST_DOWNLOADS_IN_PERIOD
        donation_settings.enabled = True
        donation_settings.save()

        # Create user a
        self.user_a = User.objects.create_user(username='user_a', email='user_a@test.com')
        self.assertIsNone(self.user_a.profile.last_donation_email_sent)

        # Create user b
        self.user_b = User.objects.create_user(username='user_b', email='user_b@test.com')
        self.assertIsNone(self.user_b.profile.last_donation_email_sent)

        # Create user c (uploader)
        self.user_c = User.objects.create_user(username='user_c', email='user_c@test.com')
        self.assertIsNone(self.user_c.profile.last_donation_email_sent)

        # Simulate a donation from the user (older than donation_settings.minimum_days_since_last_donation)
        old_donation_date = datetime.datetime.now() - datetime.timedelta(
            days=donation_settings.minimum_days_since_last_donation + 100)
        donation = donations.models.Donation.objects.create(
            user=self.user_a, amount=50.25, email=self.user_a.email, currency='EUR')
        # NOTE: use .update(created=...) to avoid field auto_now to take over
        donations.models.Donation.objects.filter(pk=donation.pk).update(created=old_donation_date)

        # Run command for sending donation emails
        call_command('donations_mails')

        # Check that user_a has been sent a reminder email and user_b has not been sent any email
        self.user_a.profile.refresh_from_db()
        self.assertIsNotNone(self.user_a.profile.last_donation_email_sent)
        user_a_last_donation_email_sent = self.user_a.profile.last_donation_email_sent
        self.assertIsNone(self.user_b.profile.last_donation_email_sent)

        # Simulate uploads from user_c
        for i in range(0, TEST_DOWNLOADS_IN_PERIOD + 1):
            sounds.models.Sound.objects.create(
                user=self.user_c,
                original_filename="Test sound %i" % i,
                base_filename_slug="test_sound_%i" % i,
                license=sounds.models.License.objects.all()[0],
                md5="fakemd5_%i" % i)
        self.user_c.profile.num_sounds = TEST_DOWNLOADS_IN_PERIOD + 1
        self.user_c.profile.save()

        # Simulate downloads from user_b
        for sound in sounds.models.Sound.objects.all():
            sounds.models.Download.objects.create(user=self.user_b, sound=sound, license=License.objects.first())

        pack = sounds.models.Pack.objects.create(user=self.user_c, name="pack")
        sounds.models.PackDownload.objects.create(user=self.user_b, pack=pack)

        # Now run the command for sending donation emails again
        call_command('donations_mails')

        # Check that user_a has not received any new email
        self.user_a.profile.refresh_from_db()
        self.assertEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)

        # Check that user_b has received an email
        self.user_b.profile.refresh_from_db()
        self.assertIsNotNone(self.user_b.profile.last_donation_email_sent)
        user_b_last_donation_email_sent = self.user_b.profile.last_donation_email_sent

        # Check that user_c has not received any email
        self.user_c.profile.refresh_from_db()
        self.assertIsNone(self.user_c.profile.last_donation_email_sent)

        # Simulate downloads from user_c
        for sound in sounds.models.Sound.objects.all():
            sounds.models.Download.objects.create(user=self.user_c, sound=sound, license=License.objects.first())

        # Run the command for sending donation emails again
        call_command('donations_mails')

        # Check that user_a has not received any new email
        self.user_a.profile.refresh_from_db()
        self.assertEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)

        # Check that user_b has not received any new email
        self.user_b.profile.refresh_from_db()
        self.assertEquals(self.user_b.profile.last_donation_email_sent, user_b_last_donation_email_sent)

        # Check that user_c has not received any new email (because he's an uploader)
        self.user_c.profile.refresh_from_db()
        self.assertIsNone(self.user_c.profile.last_donation_email_sent)

        # Change donation settings to send emails to uploaders too
        donation_settings.never_send_email_to_uploaders = False
        donation_settings.save()

        # Run the command for sending donation emails again
        call_command('donations_mails')

        # Check that user_a has not received any new email
        self.user_a.profile.refresh_from_db()
        self.assertEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)

        # Check that user_b has not received any new email
        self.user_b.profile.refresh_from_db()
        self.assertEquals(self.user_b.profile.last_donation_email_sent, user_b_last_donation_email_sent)

        # Check that now user_c has been sent an email
        self.user_c.profile.refresh_from_db()
        self.assertIsNotNone(self.user_c.profile.last_donation_email_sent)

        # Set send email to uploaders back to default
        donation_settings.never_send_email_to_uploaders = True
        donation_settings.save()

        # Now simulate that we advance time (100 days,
        # something above donation_settings.minimum_days_since_last_donation_email)
        # Change timestamps for users' last_donation_email_sent, donation objects and download objects
        time_interval = datetime.timedelta(days=donation_settings.minimum_days_since_last_donation_email + 10)
        self.user_a.profile.last_donation_email_sent -= time_interval
        self.user_b.profile.last_donation_email_sent -= time_interval
        self.user_c.profile.last_donation_email_sent -= time_interval
        self.user_a.profile.save()
        self.user_b.profile.save()
        self.user_c.profile.save()
        donation = donations.models.Donation.objects.get(pk=donation.pk)
        new_donation_created_date = donation.created - time_interval
        donations.models.Donation.objects.filter(pk=donation.pk).update(created=new_donation_created_date)
        download = sounds.models.Download.objects.first()
        new_downloads_date = download.created - time_interval
        sounds.models.Download.objects.update(created=new_downloads_date)
        user_a_last_donation_email_sent = self.user_a.profile.last_donation_email_sent
        user_b_last_donation_email_sent = self.user_b.profile.last_donation_email_sent
        user_c_last_donation_email_sent = self.user_c.profile.last_donation_email_sent

        # Now that time has passed (bigger than minimum_days_since_last_donation_email), we check again if
        # emails are sent
        call_command('donations_mails')

        # Check that user_a has not received any new email (no new downloads)
        self.user_a.profile.refresh_from_db()
        self.assertEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)

        # Check that user_b has not received any new email (no new downloads)
        self.user_b.profile.refresh_from_db()
        self.assertEquals(self.user_b.profile.last_donation_email_sent, user_b_last_donation_email_sent)

        # Check that user_c has not received any new email (no new downloads)
        self.user_c.profile.refresh_from_db()
        self.assertEquals(self.user_c.profile.last_donation_email_sent, user_c_last_donation_email_sent)

        # Now simulate downloads for all users and check again
        for sound in sounds.models.Sound.objects.all():
            sounds.models.Download.objects.create(user=self.user_a, sound=sound, license=License.objects.first())
            sounds.models.Download.objects.create(user=self.user_b, sound=sound, license=License.objects.first())
            sounds.models.Download.objects.create(user=self.user_c, sound=sound, license=License.objects.first())

        # Run command again
        call_command('donations_mails')

        # Check that user_a has received new email
        self.user_a.profile.refresh_from_db()
        self.assertNotEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)
        user_a_last_donation_email_sent = self.user_a.profile.last_donation_email_sent

        # Check that user_b has received new email
        self.user_b.profile.refresh_from_db()
        self.assertNotEquals(self.user_b.profile.last_donation_email_sent, user_b_last_donation_email_sent)

        # Check that user_c has not received any new email (he is an uploader)
        self.user_c.profile.refresh_from_db()
        self.assertEquals(self.user_c.profile.last_donation_email_sent, user_c_last_donation_email_sent)

        # Simulate user_a makes a new donation and then downloads some sounds
        donations.models.Donation.objects.create(
            user=self.user_a, amount=50.25, email=self.user_a.email, currency='EUR')
        # Reset the reminder flag to False so that in a year time user is reminded to donate
        self.user_a.profile.donations_reminder_email_sent = False
        self.user_a.profile.save()
        for sound in sounds.models.Sound.objects.all():
            sounds.models.Download.objects.create(user=self.user_a, sound=sound, license=License.objects.first())

        # Run command again
        call_command('donations_mails')

        # Check that now user_a does not receive an email beacuse he donated recently
        self.user_a.profile.refresh_from_db()
        self.assertEquals(self.user_a.profile.last_donation_email_sent, user_a_last_donation_email_sent)

    def test_donation_emails_not_sent_when_preference_disabled(self):
        donation_settings, _ = donations.models.DonationsEmailSettings.objects.get_or_create()
        TEST_DOWNLOADS_IN_PERIOD = 1
        donation_settings.downloads_in_period = TEST_DOWNLOADS_IN_PERIOD
        donation_settings.enabled = True
        donation_settings.save()

        # Create user a
        self.user_a = User.objects.create_user(username='user_a', email='user_a@test.com')
        self.assertIsNone(self.user_a.profile.last_donation_email_sent)

        # Create user b
        self.user_b = User.objects.create_user(username='user_b', email='user_b@test.com')
        self.assertIsNone(self.user_b.profile.last_donation_email_sent)

        # Create user c (uploader)
        self.user_c = User.objects.create_user(username='user_c', email='user_c@test.com')
        self.assertIsNone(self.user_c.profile.last_donation_email_sent)

        # Simulate a donation from the user (older than donation_settings.minimum_days_since_last_donation)
        old_donation_date = datetime.datetime.now() - datetime.timedelta(
            days=donation_settings.minimum_days_since_last_donation + 100)
        donation = donations.models.Donation.objects.create(
            user=self.user_a, amount=50.25, email=self.user_a.email, currency='EUR')
        # NOTE: use .update(created=...) to avoid field auto_now to take over
        donations.models.Donation.objects.filter(pk=donation.pk).update(created=old_donation_date)

        # Simulate uploads from user_c
        for i in range(0, TEST_DOWNLOADS_IN_PERIOD + 1):
            sounds.models.Sound.objects.create(
                user=self.user_c,
                original_filename="Test sound %i" % i,
                base_filename_slug="test_sound_%i" % i,
                license=sounds.models.License.objects.all()[0],
                md5="fakemd5_%i" % i)
        self.user_c.profile.num_sounds = TEST_DOWNLOADS_IN_PERIOD + 1
        self.user_c.profile.save()

        # Simulate downloads from user_b
        for sound in sounds.models.Sound.objects.all():
            sounds.models.Download.objects.create(user=self.user_b, sound=sound, license=License.objects.first())

        # Set user_a and user_b donation email preference to none
        # Create email preference object for the email type (which will mean user does not want donation
        # emails as it is enabled by default and the preference indicates user does not want it).
        email_pref = EmailPreferenceType.objects.get(name="donation_request")
        UserEmailSetting.objects.create(user=self.user_a, email_type=email_pref)
        UserEmailSetting.objects.create(user=self.user_b, email_type=email_pref)

        # Run command for sending donation emails
        call_command('donations_mails')

        # Check that both user_a and user_b have not received any email because their preferences are set to none
        self.user_a.profile.refresh_from_db()
        self.assertIsNone(self.user_a.profile.last_donation_email_sent)
        self.user_b.profile.refresh_from_db()
        self.assertIsNone(self.user_b.profile.last_donation_email_sent)
        self.assertEqual(len(mail.outbox), 0)
