from unittest import mock

import requests
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


class QueryStatsAjaxTestCase(TestCase):
    """test the /monitor/ajax_queries_stats/ endpoint"""

    fixtures = ["users"]

    def setUp(self):
        self.user = User.objects.get(username="User1")
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_stats_require_staff(self):
        self.user.is_staff = False
        self.user.save()
        for logged_in in [False, True]:
            if logged_in:
                self.client.force_login(self.user)
            else:
                self.client.logout()
            for name in [
                "queries",
                "tags",
                "sounds",
                "active-users",
                "users",
                "downloads",
                "donations",
                "totals",
                "moderator",
            ]:
                with self.subTest(logged_in=logged_in, endpoint=name):
                    self.assertEqual(self.client.get(reverse(f"monitor-{name}-stats-ajax")).status_code, 302)
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.get(reverse("monitor-totals-stats-ajax")).status_code, 200)

    @override_settings(GRAYLOG_DOMAIN="http://graylog")
    @mock.patch("requests.get")
    def test_monitor_queries_stats_ajax_error(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns an error"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 404
        resp = self.client.get(reverse("monitor-queries-stats-ajax"))

        self.assertEqual(resp.status_code, 500)
        mock_get.assert_called_with(
            "http://graylog/api/search/universal/relative/terms", auth=mock.ANY, params=mock.ANY, timeout=10
        )

    @override_settings(GRAYLOG_DOMAIN="http://graylog")
    @mock.patch("requests.get")
    def test_monitor_queries_stats_ajax_bad_data(self, mock_get):
        """The endpoint returns HTTP500 if the graylog endpoint returns 200, but the data is not JSON"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = b"<html>this is definitely not json</html>"
        resp = self.client.get(reverse("monitor-queries-stats-ajax"))

        self.assertEqual(resp.status_code, 500)
        mock_get.assert_called_with(
            "http://graylog/api/search/universal/relative/terms", auth=mock.ANY, params=mock.ANY, timeout=10
        )

    @override_settings(GRAYLOG_DOMAIN="http://graylog")
    @mock.patch("requests.get")
    def test_monitor_queries_stats_ajax_ok(self, mock_get):
        """The endpoint returns valid data if graylog returns valid data"""
        mock_get.return_value = requests.Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value._content = b'{"response": "ok"}'

        resp = self.client.get(reverse("monitor-queries-stats-ajax"))

        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {"response": "ok"})
        mock_get.assert_called_with(
            "http://graylog/api/search/universal/relative/terms", auth=mock.ANY, params=mock.ANY, timeout=10
        )
