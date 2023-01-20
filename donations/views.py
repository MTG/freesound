from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
import base64
import json
import logging
import urllib.parse

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from .forms import DonateForm, BwDonateForm
from .models import Donation, DonationCampaign
from utils.frontend_handling import render, using_beastwhoosh, BwCompatibleTemplateResponse
from utils.mail import send_mail_template

web_logger = logging.getLogger('web')


def _save_donation(encoded_data, email, amount, currency, transaction_id, source):
    extra_data = json.loads(base64.b64decode(encoded_data))
    campaign = DonationCampaign.objects.get(id=extra_data['campaign_id'])
    is_anonymous = False
    user = None
    user_id = None
    display_name = None

    if 'user_id' in extra_data:
        user = User.objects.get(id=extra_data['user_id'])
        user_id = user.id
        email = user.profile.get_email_for_delivery()
        # Reset the reminder flag to False so that in a year time user is reminded to donate
        user.profile.donations_reminder_email_sent = False
        user.profile.save()

    if 'name' in extra_data:
        is_anonymous = True
        display_name = extra_data['name']

    donation_data = {
        'email': email,
        'display_name': display_name,
        'amount': amount,
        'currency': currency,
        'display_amount': extra_data['display_amount'],
        'is_anonymous': is_anonymous,
        'user': user,
        'campaign': campaign,
        'source': source
    }
    donation, created = Donation.objects.get_or_create(transaction_id=transaction_id, defaults=donation_data)

    if created:
        email_to = None if user is not None else email
        send_mail_template(
                settings.EMAIL_SUBJECT_DONATION_THANK_YOU,
                'donations/email_donation.txt', {
                    'user': user,
                    'amount': amount,
                    'display_name': display_name
                    }, user_to=user, email_to=email_to)

        log_data = donation_data
        log_data.update({'user_id': user_id})
        log_data.update({'created': str(donation.created)})
        del log_data['user']  # Don't want to serialize user
        del log_data['campaign']  # Don't want to serialize campaign
        log_data['amount_float'] = float(log_data['amount'])
        web_logger.info('Recevied donation (%s)' % json.dumps(log_data))
    return True


@csrf_exempt
def donation_complete_stripe(request):
    """
    This view is called from Stripe when a new donation is completed, here we create and
    store the donation in the db.
    """
    if "HTTP_STRIPE_SIGNATURE" in request.META:
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        stripe.api_key = settings.STRIPE_PRIVATE_KEY
        event = None

        try:
            event = stripe.Webhook.construct_event(
              payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return HttpResponse(status=400)

        # Handle the checkout.session.completed event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            # Fulfill the purchase...
            amount = int(session['display_items'][0]['amount'])/100.0
            encoded_data = session['success_url'].split('?')[1].replace("token=", "")
            customer_email = session['customer_email']
            if customer_email == None:
                customer = stripe.Customer.retrieve(session['customer'])
                customer_email = customer['email']
            _save_donation(encoded_data, customer_email, amount, 'EUR', session['id'], 's')

        return HttpResponse(status=200)
    return HttpResponse(status=400)


@csrf_exempt
def donation_success(request):
    """
    This user reaches this view from sripe when the credit card was valid, here we only
    add a message to the user and redirect to donations page.
    """
    messages.add_message(request, messages.INFO, 'Thanks! we will process you donation and send you an email soon.')
    return redirect('donate')


@csrf_exempt
def donation_complete_paypal(request):
    """
    This view listens to a notification made from paypal when someone makes
    a donation, it validates the data and then stores the donation.
    """
    params = request.POST.copy()
    params.update({'cmd': '_notify-validate'})

    if "mc_gross" in params:
        # Paypal makes notifications of different events e.g: new suscriptions,
        # we only want to save when the actual payment happends
        params = request.POST.copy()
        params.update({'cmd': '_notify-validate'})

        try:
            req = requests.post(settings.PAYPAL_VALIDATION_URL, data=params)
        except requests.exceptions.Timeout:
            web_logger.error("Can't verify donations information with paypal")
            return HttpResponse("FAIL")

        if req.text == 'VERIFIED':
             _save_donation(params['custom'],
                params['payer_email'],
                params['mc_gross'],
                params['mc_currency'],
                params['txn_id'],
                'p')
    return HttpResponse("OK")


def donation_session_stripe(request):
    ''' Creates a Stripe session object and gets a session id which is used in
    the frontend to during the redirect to stripe website.
    '''
    stripe.api_key = settings.STRIPE_PRIVATE_KEY
    if request.method == 'POST':
        FormToUse = BwDonateForm if using_beastwhoosh(request) else DonateForm
        form = FormToUse(request.POST, user=request.user)
        if form.is_valid():
            email_to = request.user.email if request.user.is_authenticated() else None
            amount = form.cleaned_data['amount']
            domain = "https://%s" % Site.objects.get_current().domain
            return_url_success = urllib.parse.urljoin(domain, reverse('donation-success'))
            return_url_success += '?token={}'.format(form.encoded_data)
            return_url_cancel = urllib.parse.urljoin(domain, reverse('donate'))
            session = stripe.checkout.Session.create(
                customer_email=email_to,
                payment_method_types=['card'],
                line_items=[{
                    'name': 'Freesound donation',
                    'description': 'Donation for freesound.org',
                    'images': ['https://freesound.org/media/images/logo.png'],
                    'amount': int(amount*100),
                    'currency': 'eur',
                    'quantity': 1,
                }],
              success_url=return_url_success,
              cancel_url=return_url_cancel,
            )
            return JsonResponse({"session_id":session.id})
        else:
            return JsonResponse({'errors': form.errors})
    # If request is GET return an error 400
    return HttpResponse(status=400)


def donation_session_paypal(request):
    ''' Donate page: display form for donations where if user is logged in
    we give the option to doneate anonymously otherwise we just give the option
    to enter the name that will be displayed.
    If request is post we generate the data to send to paypal.
    '''
    if request.method == 'POST':
        FormToUse = BwDonateForm if using_beastwhoosh(request) else DonateForm
        form = FormToUse(request.POST, user=request.user)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            returned_data_str = form.encoded_data
            domain = "https://%s" % Site.objects.get_current().domain
            return_url = urllib.parse.urljoin(domain, reverse('donation-complete-paypal'))
            data = {"url": settings.PAYPAL_VALIDATION_URL,
                    "params": {
                        "cmd": "_donations",
                        "currency_code": "EUR",
                        "business": settings.PAYPAL_EMAIL,
                        "item_name": "Freesound donation",
                        "custom": returned_data_str,
                        "notify_url": return_url,
                        "no_shipping": 1,
                        "lc": "en_US"
                        }
                    }

            if form.cleaned_data['recurring']:
                data['params']['cmd'] = '_xclick-subscriptions'
                data['params']['a3'] = amount
                # src - indicates recurring subscription
                data['params']['src'] = 1
                # p3 - number of time periods between each recurrence
                data['params']['p3'] = 1
                # t3 - time period (D=days, W=weeks, M=months, Y=years)
                data['params']['t3'] = 'M'
                # sra - Number of times to reattempt on failure
                data['params']['sra'] = 1
                data['params']['item_name'] = 'Freesound monthly donation'
            else:
                data['params']['amount'] = amount
        else:
            data = {'errors': form.errors}
        return JsonResponse(data)
    # If request is GET redirect to donations page
    return HttpResponseRedirect(reverse('donate'))


def donate(request):
    """Donate page: display form for donations where if user is logged in we give the option to donate anonymously
    otherwise we just give the option to enter the name that will be displayed. If request is post we generate the
    data to send to paypal or stripe.
    """
    default_donation_amount = request.GET.get(settings.DONATION_AMOUNT_REQUEST_PARAM, None)
    FormToUse = BwDonateForm if using_beastwhoosh(request) else DonateForm
    form = FormToUse(user=request.user, default_donation_amount=default_donation_amount)
    tvars = {'form': form, 'stripe_key': settings.STRIPE_PUBLIC_KEY}
    return render(request, 'donations/donate.html', tvars)


class DonationsList(ListView):
    response_class = BwCompatibleTemplateResponse
    model = Donation
    paginate_by = settings.DONATIONS_PER_PAGE
    ordering = ["-created"]


def donate_redirect(request):
    return HttpResponseRedirect(reverse('donate'))
