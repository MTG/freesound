import json
import base64
import requests
import urlparse
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from models import Donation, DonationCampaign
from utils.mail import send_mail_template


@csrf_exempt
def donation_complete(request):
    '''This view listens to a notification made from paypal when someone makes
    a donation, it validates the data and then stores the donation.
    '''
    params = {'cmd': '_notify-validate'}
    for key, value in request.POST.items():
        params[key] =  value
    req = requests.post(settings.PAYPAL_VALIDATION_URL, data=params)
    if req.text == 'VERIFIED':
        extra_data = json.loads(base64.b64decode(params['custom']))
        campaign = DonationCampaign.objects.get(id=extra_data['campaign_id'])
        user = None
        if 'user_id' in extra_data:
            user = User.objects.get(id=extra_data['user_id'])

        Donation.objects.get_or_create(transaction_id=params['txn_id'], defaults={
            'email': params['payer_email'],
            'display_name': extra_data['name'],
            'amount': params['mc_gross'],
            'currency': params['mc_currency'],
            'user': user,
            'campaign': campaign})

        send_mail_template(\
                u'Donation',
                'donations/email_donation.txt',
                {'user': user, 'amount': params['mc_gross'], 'display_name': extra_data['name']},
                None, params['payer_email'])
    return HttpResponse("OK")


def donate(request):
    ''' Donate page: display form for donations where if user is logged in
    we give the option to doneate anonymously otherwise we just give the option
    to enter the name that will be displayed.
    If request is post we generate the data to send to paypal.
    '''
    if request.method == 'POST':
        name = request.POST.get('name', None)
        campaign = DonationCampaign.objects.order_by('date_start').last()
        returned_data = {'name': name, "campaign_id": campaign.id}
        annon = request.POST.get('annon', None)

        # If the donation is annonymous we don't store the user
        if annon == '1':
            returned_data['name'] = "Anonymous"
        elif request.user :
            returned_data['user_id'] = request.user.id

        # Paypal gives only one field to add extra data so we send it as b64
        returned_data_str = base64.b64encode(json.dumps(returned_data))
        domain = "https://%s" % Site.objects.get_current().domain
        return_url = urlparse.urljoin(domain, reverse('donation-complete'))

        data = {"url": settings.PAYPAL_VALIDATION_URL,
                "params": {
                    "cmd": "_donations",
                    "currency_code": "EUR",
                    "business": settings.PAYPAL_EMAIL,
                    "item_name": "Freesound",
                    "custom": returned_data_str,
                    "notify_url": return_url}}
        return JsonResponse(data)
    else:
        tvars = {}
        return render(request, 'donations/donate.html', tvars)


class DonationsList(ListView):
    model = Donation
    paginate_by = 15
    ordering = ["-created"]
