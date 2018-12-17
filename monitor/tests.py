import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
import requests

import mock


class QueryStatsAjaxTestCase(TestCase):
    """test the /monitor/ajax_queries_stats/ endpoint"""

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_error(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns an error"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 404
        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEquals(resp.status_code, 500)
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY)

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_bad_data(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns 200, but the data is not JSON"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = '<html>this is definitely not json</html>'
        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEquals(resp.status_code, 500)
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY)

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_ok(self, mock_get):
        """The endpoint returns valid data if graylog returns valid data"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = '{"response": "ok"}'

        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEquals(resp.status_code, 200)
        self.assertEquals(json.loads(resp.content), {'response': 'ok'})
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY)


class UsageStatsAjaxTestCase(TestCase):
    """test the /monitor/ajax_api_usage_stats/<client-id> endpoint"""

    def setUp(self):
        user = User.objects.create_superuser(username='test', email='test@freesound.org', password='test')
        self.client.force_login(user)

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_error(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns an error"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 404
        resp = self.client.get(reverse('monitor-api-stats-ajax', kwargs={'client_id': 'test'}))

        self.assertEquals(resp.status_code, 500)
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/histogram', auth=mock.ANY, params=mock.ANY)

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_bad_data(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns 200, but the data is not JSON"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = '<html>this is definitely not json</html>'
        resp = self.client.get(reverse('monitor-api-stats-ajax', kwargs={'client_id': 'test'}))

        self.assertEquals(resp.status_code, 500)
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/histogram', auth=mock.ANY, params=mock.ANY)

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_ok(self, mock_get):
        """The endpoint returns valid data if graylog returns valid data"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = '{"response": "ok"}'

        resp = self.client.get(reverse('monitor-api-stats-ajax', kwargs={'client_id': 'test'}))

        self.assertEquals(resp.status_code, 200)
        self.assertEquals(json.loads(resp.content), {'response': 'ok'})
        mock_get.assert_called_with('http://graylog/graylog/api/search/universal/relative/histogram', auth=mock.ANY, params=mock.ANY)
