import json
import base64
import requests
import urlparse
import logging
from django.shortcuts import render
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from models import Donation, DonationCampaign
from forms import DonateForm
from utils.mail import send_mail_template

logger = logging.getLogger('web')


@csrf_exempt
def donation_complete(request):
    """
    This view listens to a notification made from paypal when someone makes
    a donation, it validates the data and then stores the donation.
    """
    params = request.POST.copy()
    params.update({'cmd': '_notify-validate'})

    try:
        req = requests.post(settings.PAYPAL_VALIDATION_URL, data=params)
    except requests.exceptions.Timeout:
        logger.error("Can't verify donations information with paypal")
        return HttpResponse("FAIL")

    if req.text == 'VERIFIED':
        extra_data = json.loads(base64.b64decode(params['custom']))
        email = params['payer_email']
        campaign = DonationCampaign.objects.get(id=extra_data['campaign_id'])
        is_anonymous = False
        user = None
        user_id = None
        display_name = None

        if 'user_id' in extra_data:
            user = User.objects.get(id=extra_data['user_id'])
            user_id = user.id
            email = user.email
            # Reset the reminder flag to False so that in a year time user is reminded to donate
            user.profile.donations_reminder_email_sent = False
            user.profile.save()

        if 'name' in extra_data:
            is_anonymous = True
            display_name = extra_data['name']

        donation_data = {
            'email': params['payer_email'],
            'display_name': display_name,
            'amount': params['mc_gross'],
            'currency': params['mc_currency'],
            'display_amount': extra_data['display_amount'],
            'is_anonymous': is_anonymous,
            'user': user,
            'campaign': campaign}
        Donation.objects.get_or_create(transaction_id=params['txn_id'], defaults=donation_data)

        send_mail_template(
                u'Thanks for your donation!',
                'donations/email_donation.txt', {
                    'user': user,
                    'amount': params['mc_gross'],
                    'display_name': display_name
                    }, None, email)

        log_data = donation_data
        log_data.update({'user_id': user_id})
        del log_data['user']  # Don't want to serialize user
        del log_data['campaign']  # Don't want to serialize campaign
        log_data['amount_float'] = float(log_data['amount'])
        logger.info('Recevied donation (%s)' % json.dumps(log_data))
    return HttpResponse("OK")


def donate(request):
    ''' Donate page: display form for donations where if user is logged in
    we give the option to doneate anonymously otherwise we just give the option
    to enter the name that will be displayed.
    If request is post we generate the data to send to paypal.
    '''
    if request.method == 'POST':
        form = DonateForm(request.POST, user=request.user)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            returned_data_str = form.encoded_data
            domain = "https://%s" % Site.objects.get_current().domain
            return_url = urlparse.urljoin(domain, reverse('donation-complete'))
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
    else:
        form = DonateForm(user=request.user)
        tvars = {'form': form}
        return render(request, 'donations/donate.html', tvars)


class DonationsList(ListView):
    model = Donation
    paginate_by = settings.DONATIONS_PER_PAGE
    ordering = ["-created"]


def donate_redirect(request):
    return HttpResponseRedirect(reverse('donate'))
