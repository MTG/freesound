'''
Copyright 2013 Otto Yiu and other contributors
http://ottoyiu.com

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''


import re
from django import http
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from utils.corsheaders import defaults as settings


ACCESS_CONTROL_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
ACCESS_CONTROL_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
ACCESS_CONTROL_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
ACCESS_CONTROL_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
ACCESS_CONTROL_ALLOW_METHODS = 'Access-Control-Allow-Methods'
ACCESS_CONTROL_MAX_AGE = 'Access-Control-Max-Age'


class CorsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        '''
            If CORS preflight header, then create an empty body response (200 OK) and return it

            Django won't bother calling any other request view/exception middleware along with
            the requested view; it will call any response middlewares
        '''
        if (self.is_enabled(request) and
            request.method == 'OPTIONS' and
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META):
            response = http.HttpResponse()
            return response
        response = self.get_response(request)

        #Add the respective CORS headers

        origin = request.META.get('HTTP_ORIGIN')
        if self.is_enabled(request) and origin:
            # todo: check hostname from db instead
            url = urlparse(origin)

            if not settings.CORS_ORIGIN_ALLOW_ALL and self.origin_not_found_in_white_lists(origin, url):
                return response

            response[ACCESS_CONTROL_ALLOW_ORIGIN] = "*" if settings.CORS_ORIGIN_ALLOW_ALL else origin

            if len(settings.CORS_EXPOSE_HEADERS):
                response[ACCESS_CONTROL_EXPOSE_HEADERS] = ', '.join(settings.CORS_EXPOSE_HEADERS)

            if settings.CORS_ALLOW_CREDENTIALS:
                response[ACCESS_CONTROL_ALLOW_CREDENTIALS] = 'true'

            if request.method == 'OPTIONS':
                response[ACCESS_CONTROL_ALLOW_HEADERS] = ', '.join(settings.CORS_ALLOW_HEADERS)
                response[ACCESS_CONTROL_ALLOW_METHODS] = ', '.join(settings.CORS_ALLOW_METHODS)
                if settings.CORS_PREFLIGHT_MAX_AGE:
                    response[ACCESS_CONTROL_MAX_AGE] = settings.CORS_PREFLIGHT_MAX_AGE

        return response

    def origin_not_found_in_white_lists(self, origin, url):
        return url.netloc not in settings.CORS_ORIGIN_WHITELIST and not self.regex_domain_match(origin)

    def regex_domain_match(self, origin):
        for domain_pattern in settings.CORS_ORIGIN_REGEX_WHITELIST:
            if re.match(domain_pattern, origin):
                return origin

    def is_enabled(self, request):
        return re.match(settings.CORS_URLS_REGEX, request.path)
