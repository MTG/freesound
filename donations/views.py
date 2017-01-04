import requests
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from models import Donation, DonationCampaign


@csrf_exempt
def donation_complete(request):
    params = {'cmd': '_notify-validate'}
    for key, value in request.POST.items():
        params[key] =  value
    if settings.DEBUG:
        paypal_validation_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
    else:
        paypal_validation_url = "https://www.paypal.com/cgi-bin/webscr"
    req = requests.post(paypal_validation_url, data=params)
    if req.text == 'VERIFIED':
        campaign = DonationCampaign.objects.order_by('date_start').last()
        Donation.objects.get_or_create(transaction_id=params['txn_id'], defaults={
        'email': params['payer_email'],
        'display_name': params['custom'],
        'amount': params['mc_gross'],
        'currency': params['mc_currency'],
        'campaign': campaign})
    return HttpResponse("OK")


def donate(request):
    tvars = {'paypal_email': settings.PAYPAL_EMAIL}
    return render(request, 'donations/donate.html', tvars)


class DonationsList(ListView):
    model = Donation
    paginate_by = 15
    ordering = ["-created"]
