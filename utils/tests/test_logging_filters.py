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
import json
import logging

from django.test import TestCase
from django.urls import reverse

from utils.logging_filters import get_client_ip, APILogsFilter, GenericDataFilter
from utils.test_helpers import create_user_and_sounds


class DummyRequest:
    """A dummy request to check the X-Forwarded-For header in logging_filters.get_client_ip"""
    def __init__(self, xforwardedfor):
        self.headers = {"x-forwarded-for": xforwardedfor}


class LogRecordsStoreHandler(logging.Handler):
    """
    A logger handler class which stores LogRecord entries in a list
    Inspiration from: https://stackoverflow.com/questions/57420008/python-after-logging-debug-how-to-view-its-logrecord
    """
    def __init__(self, records_list):
        self.records_list = records_list
        super().__init__()

    def emit(self, record):
        self.records_list.append(record)


class LoggingFiltersTest(TestCase):
    fixtures = ['licenses']

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

    def test_generic_log_data_filter(self):
        logs_list = []
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addFilter(GenericDataFilter())
        logger.addHandler(LogRecordsStoreHandler(logs_list))

        for count, (log_message, properties_to_check_in_output) in enumerate([
            ("Simple message without json-formatted part", {}),
            ("Simple message with nòn-ascií characters", {}),
            (f"Rate limited IP ({json.dumps({'ip': '1.1.1.1', 'path': 'testPath/'})})", {
                'ip': '1.1.1.1',
                'path': 'testPath/',
            }),
        ]):
            logger.debug(log_message)
            log_record = logs_list[count]
            self.assertEqual(log_message, log_record.msg)
            for prop, value in properties_to_check_in_output.items():
                self.assertTrue(hasattr(log_record, prop))
                self.assertEqual(getattr(log_record, prop), value)

    def test_api_log_filter(self):
        logs_list = []
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        logger.addFilter(APILogsFilter())
        logger.addHandler(LogRecordsStoreHandler(logs_list))

        for count, (log_message, properties_to_check_in_output) in enumerate([
            ('410 API error: End of life', {}),
            ('sound:376958 instance #!# {"fields": "id,url,name,duration,download,previews", '
             '"filter": "license:%22Creative%20Commons%200%22"} #!# {"api_version": "v2", "api_auth_type": "Token", '
             '"api_client_username": "test_uname", "api_enduser_username": "None", "api_client_id": '
             '"fake_id", "api_client_name": "Test àpp", "ip": "1.1.1.1", '
             '"api_request_protocol": "https", "api_www": "none"}', {
                'api_resource': 'sound instance',
                'fields': 'id,url,name,duration,download,previews',
                'filter': 'license:"Creative Commons 0"',
                'api_client_username': 'test_uname',
                'api_client_name': 'Test àpp'
            }),  # Note: I'm only testing a couple of fields as the test is complete enough with that
        ]):
            logger.debug(log_message)
            log_record = logs_list[count]
            self.assertEqual(log_message, log_record.msg)
            for prop, value in properties_to_check_in_output.items():
                self.assertTrue(hasattr(log_record, prop))
                self.assertEqual(getattr(log_record, prop), value)

    def test_api_view_with_logging(self):
        user, _, _ = create_user_and_sounds(num_sounds=1, num_packs=0)
        self.client.force_login(user)
        logs_list = []
        logger = logging.getLogger("api")
        logger.addHandler(LogRecordsStoreHandler(logs_list))
        logger.addFilter(APILogsFilter())
        query_params = {
            'query': 'dogs',
            'fields': 'id,url,name,duration,download,previews',
            'filter': 'license:"Creative Commons 0"'
        }
        params = '&'.join([f'{key}={value}' for key, value in query_params.items()])
        self.client.get(reverse('apiv2-sound-search') + f'?{params}')
        log_record = logs_list[0]

        for prop, value in query_params.items():
            self.assertTrue(hasattr(log_record, prop))
            self.assertEqual(getattr(log_record, prop), value)



