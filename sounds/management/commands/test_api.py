# -*- coding: utf-8 -*-

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

import requests
import json
from django.core.management.base import BaseCommand
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
    help = "Test apiv2 with examples from apiv2/examples.py"

    def handle(self,  *args, **options):
        if args:
            section = str(args[0])
        else:
            section = False

        client = ApiV2Client.objects.filter(user__username='frederic.font')[0]
        token = client.client_secret
        base_url = "http://%s/" % Site.objects.get_current().domain

        ok = list()
        failed = list()
        error = list()

        print ''
        for key, items in examples.items():
            if 'Download' not in key:
                if section:
                    if section not in key:
                        continue

                print 'Testing %s' % key
                print '--------------------------------------'

                for desc, urls in items:
                    for url in urls:
                        if url[0:4] != 'curl':
                            prepended_url = base_url + url
                            print '- %s' % prepended_url,
                            try:
                                r = api_request(prepended_url, token=token)
                                if r.status_code == 200:
                                    print 'OK'
                                    ok.append(prepended_url)
                                else:
                                    print 'FAIL! (%i)' % r.status_code
                                    failed.append((prepended_url, r.status_code))
                            except Exception, e:
                                print 'ERROR (%s)' % str(e)
                                error.append(prepended_url)

                print ''

        print '\nRUNNING TESTS FINISHED:'
        print '\t%i tests completed successfully' % len(ok)
        if error:
            print '\t%i tests gave errors (connection, etc...)' % len(error)
        print '\t%i tests failed' % len(failed)
        for url, status_code in failed:
            print '\t\t- %s (%i)' % (url, status_code)

