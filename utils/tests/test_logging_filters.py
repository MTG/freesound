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
from django.test import TestCase

from utils.logging_filters import get_client_ip


class DummyRequest:
    """A dummy request to check the X-Forwarded-For header in logging_filters.get_client_ip"""
    def __init__(self, xforwardedfor):
        self.META = {"HTTP_X_FORWARDED_FOR": xforwardedfor}

class LoggingFiltersTest(TestCase):

    def test_get_client_ip_valid(self):
        req = DummyRequest('127.0.0.1,10.10.10.10')
        ip = get_client_ip(req)
        self.assertEqual(ip, '127.0.0.1')

        # It doesn't matter if any further items are invalid, we only use the first
        req = DummyRequest('127.0.0.1,foo')
        ip = get_client_ip(req)
        self.assertEqual(ip, '127.0.0.1')

    def test_get_client_ip_empty(self):
        req = DummyRequest(None)
        ip = get_client_ip(req)
        self.assertEqual(ip, '-')

        req = DummyRequest('')
        ip = get_client_ip(req)
        self.assertEqual(ip, '-')

    def test_get_client_ip_invalid(self):
        req = DummyRequest('foo')
        ip = get_client_ip(req)
        self.assertEqual(ip, '-')

        req = DummyRequest('foo,127.0.0.1')
        ip = get_client_ip(req)
        self.assertEqual(ip, '-')
