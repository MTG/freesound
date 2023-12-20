# PayPal python NVP API wrapper class.
# This is a sample to help others get started on working
# with the PayPal NVP API in Python.
# This is not a complete reference! Be sure to understand
# what this class is doing before you try it on production servers!
# ...use at your own peril.

# see https://www.paypal.com/IntegrationCenter/ic_nvp.html
# and
# https://www.paypal.com/en_US/ebook/PP_NVPAPI_DeveloperGuide/index.html
# for more information.

# by Mike Atlas / LowSingle.com / MassWrestling.com, September 2007
# No License Expressed. Feel free to distribute, modify,
# and use in any open or closed source project without credit to the author

# lot's of changed by Bram de Jong, but no fundamental changes to how the
# paypal API works, just cleanups. Also removed the DoDirectPayment method as
# it is not needed for Freesound

# Example usage:
# 1.
#   paypal = Paypal()
#   response = paypal.set_express_checkout(100)
#   url = paypal.get_paypal_forward_url(response['token'])
#   HttpResponseRedirect(url)
#
# 2.
#   paypal = Paypal()
#   # customer details are in:
#   response = paypal.get_express_checkout_details(request.GET["TOKEN"])
#   # the actual payment
#   response = paypal.do_express_checkout_payment(request.GET["TOKEN"], request.GET["PayerID"], 100)
#   # if you want to get all info:
#   paypal.get_transaction_details(response['transactionid'])

import urllib.request, urllib.parse, urllib.error


class Paypal:

    def __init__(self, debug=True):
        # fill these in with the API values
        self.signature = dict(
            user='sdk-three_api1.sdk.com',
            pwd='QFZCWN5HZM8VBG7Q',
            signature='A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
            version='3.0',
        )

        self.urls = dict(
            returnurl='http://www.test.com/',
            cancelurl='http://www.test.com/cancelurl',
        )

        self.debug = debug

        if debug:
            self.API_ENDPOINT = 'https://api-3t.sandbox.paypal.com/nvp'
        else:
            self.API_ENDPOINT = 'https://api-3t.paypal.com/nvp'

    def get_paypal_forward_url(self, token):
        if self.debug:
            return 'https://www.sandbox.paypal.com/webscr?cmd=_express-checkout&token=' + token
        else:
            return 'https://www.paypal.com/webscr?cmd=_express-checkout&token=' + token

    def query(self, parameters, add_urls=True):
        """for a dict of parameters, create the query-string, get the paypal URL and return the parsed dict"""
        params = list(self.signature.items()) + list(parameters.items())

        print(parameters)

        if add_urls:
            params += list(self.urls.items())

        # encode the urls into a query string
        params_string = urllib.parse.urlencode(params)

        # get the response and parse it
        response = urllib.parse.parse_qs(urllib.request.urlopen(self.API_ENDPOINT, params_string).read())

        # the parsed dict has a list for each value, but all Paypal replies are unique
        return {key.lower(): value[0] for (key, value) in response.items()}

    def set_express_checkout(self, amount):
        """Set up an express checkout"""
        params = dict(
            method="SetExpressCheckout",
            noshipping=1,
            paymentaction='Authorization',
            amt=amount,
            currencycode='EUR',
            email='',    # used by paypal to set email for account creation
            desc='Freesound donation of %d euro' % amount,    # description of what the person is buying
            custom=amount,    # custom field, can be anything you want
            hdrimg='',    # url to image for header, recomended to be stored on https server 
        )

        return self.query(params)

    def get_express_checkout_details(self, token):
        """Once the user returns to the return url, call this to get the detailsthe user returns to the return url, call this"""
        params = dict(
            method="GetExpressCheckoutDetails",
            token=token,
        )

        return self.query(params)

    def do_express_checkout_payment(self, token, payer_id, amt):
        """do the actual transaction..."""
        params = dict(
            method="DoExpressCheckoutPayment",
            paymentaction='Sale',
            token=token,
            amt=amt,
            currencycode='EUR',
            payerid=payer_id
        )

        return self.query(params)

    def get_transaction_details(self, tx_id):
        """get all the details of a transaction that has finished"""
        params = dict(method="GetTransactionDetails", transactionid=tx_id)

        return self.query(params, add_urls=False)
