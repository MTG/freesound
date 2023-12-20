from unittest import mock

import requests
from django.test import TestCase, override_settings
from django.urls import reverse


class QueryStatsAjaxTestCase(TestCase):
    """test the /monitor/ajax_queries_stats/ endpoint"""

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_error(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns an error"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 404
        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEqual(resp.status_code, 500)
        mock_get.assert_called_with(
            'http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY
        )

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_bad_data(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns 200, but the data is not JSON"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = b'<html>this is definitely not json</html>'
        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEqual(resp.status_code, 500)
        mock_get.assert_called_with(
            'http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY
        )

    @override_settings(GRAYLOG_DOMAIN='http://graylog')
    @mock.patch('requests.get')
    def test_monitor_queries_stats_ajax_ok(self, mock_get):
        """The endpoint returns valid data if graylog returns valid data"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = b'{"response": "ok"}'

        resp = self.client.get(reverse('monitor-queries-stats-ajax'))

        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'response': 'ok'})
        mock_get.assert_called_with(
            'http://graylog/graylog/api/search/universal/relative/terms', auth=mock.ANY, params=mock.ANY
        )
