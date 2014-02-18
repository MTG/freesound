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


from django.conf import settings

default_headers = (
    'x-requested-with',
    'content-type',
    'accept',
    'origin',
    'authorization',
    'x-csrftoken',
)
CORS_ALLOW_HEADERS = getattr(settings, 'CORS_ALLOW_HEADERS', default_headers)

default_methods = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
)
CORS_ALLOW_METHODS = getattr(settings, 'CORS_ALLOW_METHODS', default_methods)

CORS_ALLOW_CREDENTIALS = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)

CORS_PREFLIGHT_MAX_AGE = getattr(settings, 'CORS_PREFLIGHT_MAX_AGE', 86400)

CORS_ORIGIN_ALLOW_ALL = getattr(settings, 'CORS_ORIGIN_ALLOW_ALL', True)

CORS_ORIGIN_WHITELIST = getattr(settings, 'CORS_ORIGIN_WHITELIST', ())

CORS_ORIGIN_REGEX_WHITELIST = getattr(settings, 'CORS_ORIGIN_REGEX_WHITELIST', ())

CORS_EXPOSE_HEADERS = getattr(settings, 'CORS_EXPOSE_HEADERS', ())

CORS_URLS_REGEX = getattr(settings, 'CORS_URLS_REGEX', '^.*$')
