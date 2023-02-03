#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

try:
    import requests
except:
    # Ignore requests and let the command fail if requests not installed. This tests will eventually be moved
    # into unit tests using the standard django framework.
    pass
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from apiv2.models import ApiV2Client
from apiv2.examples import examples


def api_request(full_url, type='GET', post_data=None, auth='token', token=None):

    if '?' not in full_url:
        url = full_url
        params = dict()
    else:
        url = full_url.split('?')[0]
        params = dict()
        for param in full_url.split('?')[1].split('&'):
            name = param.split('=')[0]
            value = '='.join(param.split('=')[1:])
            params[name] = value

    if post_data:
        data = json.dumps(post_data)

    if auth == 'token':
        headers = {'Authorization': 'Token %s' % token }

    if type == 'GET':
        r = requests.get(url, params=params, headers=headers)
    elif type == 'POST':
        r = requests.post(url, params=params, data=data, headers=headers)

    return r


class Command(BaseCommand):
    help = "Test apiv2 with examples from apiv2/examples.py. " \
           "Usage: python manage.py basic_api_tests [custom_base_url] [token] [section]"

    def add_arguments(self, parser):
        parser.add_argument(
            '--base_url',
            action='store',
            dest='base_url',
            default=False,
            help='base url where to run the tests')
        parser.add_argument(
            '--token',
            action='store',
            dest='token',
            default=False,
            help='api token (client secret) to use')
        parser.add_argument(
            '--section',
            action='store',
            dest='section',
            default=False,
            help='section of the tests to run')

    def handle(self,  *args, **options):
        base_url = options['base_url']
        token = options['token']
        section = options['section']

        if not base_url:
            base_url = "https://%s/" % Site.objects.get_current().domain

        test_client = None
        if not token:
            # If testing locally (localhost) there is no need to provide an API token because it can be generated
            # automatically and then deleted after the tests
            user = User.objects.first()
            test_client = ApiV2Client.objects.create(user=user, throttling_level=99)
            token = test_client.client_secret

        ok = list()
        failed = list()
        error = list()

        print('')
        for key, items in examples.items():
            if 'Download' not in key:
                if section:
                    if section not in key:
                        continue

                print('Testing %s' % key)
                print('--------------------------------------')

                for desc, urls in items:
                    for url in urls:
                        if url[0:4] != 'curl':
                            prepended_url = base_url + url
                            print('- %s' % prepended_url, end=' ')
                            try:
                                r = api_request(prepended_url, token=token)
                                if r.status_code == 200:
                                    print('OK')
                                    ok.append(prepended_url)
                                else:
                                    print('FAIL! (%i)' % r.status_code)
                                    failed.append((prepended_url, r.status_code))
                            except Exception as e:
                                print('ERROR (%s)' % str(e))
                                error.append(prepended_url)

                print('')

        print('\nRUNNING TESTS FINISHED:')
        print('\t%i tests completed successfully' % len(ok))
        if error:
            print('\t%i tests gave errors (connection, etc...)' % len(error))
        print('\t%i tests failed' % len(failed))
        for url, status_code in failed:
            print('\t\t- %s (%i)' % (url, status_code))

        if test_client is not None:
            test_client.delete()
