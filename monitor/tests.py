import datetime
from decimal import Decimal
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from donations.models import Donation, DonationRequest
from monitor import donations_stats


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


def _pick(d, *keys):
    return tuple(d[k] for k in keys)


class DonationsStatsAjaxTestCase(TestCase):
    """test the /monitor/ajax_donations_stats/ endpoint and the donations panel"""

    fixtures = ["users"]

    def setUp(self):
        self.user = User.objects.get(username="User1")
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def _donate(self, amount, created, user=None, email="donor@example.com", source="p"):
        donation = Donation.objects.create(
            user=user, email=email, amount=Decimal(amount), currency="EUR", source=source
        )
        # `created` uses auto_now_add, so set it with an update
        Donation.objects.filter(id=donation.id).update(created=created)

    def _request(self, user, request_type, created):
        request = DonationRequest.objects.create(user=user, request_type=request_type)
        DonationRequest.objects.filter(id=request.id).update(created=created)

    def _local_dt(self, year, month, day, hour=12):
        return timezone.make_aware(datetime.datetime(year, month, day, hour))

    def test_donations_panel(self):
        resp = self.client.get(reverse("monitor-donations"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse("monitor-donations-stats-ajax"))
        self.assertNotContains(self.client.get(reverse("monitor-stats")), "Donations in the last 12 months")

    def test_donations_panel_requires_staff(self):
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.client.get(reverse("monitor-donations")).status_code, 302)

    @mock.patch("monitor.views.timezone.localdate", return_value=datetime.date(2026, 3, 15))
    def test_default_ranges(self, _):
        self._donate("10.00", self._local_dt(2026, 3, 15))
        self._donate("5.50", self._local_dt(2026, 3, 15, 18))
        self._donate("2.25", self._local_dt(2026, 2, 14))  # 29 days before: first day of the daily range
        self._donate("100.00", self._local_dt(2026, 2, 13))  # 30 days before: out of the daily range
        self._donate("7.00", self._local_dt(2024, 10, 1))  # first day of the 18 month range
        self._donate("50.00", self._local_dt(2024, 9, 30))  # out of the monthly range
        self._donate("3.00", self._local_dt(2021, 6, 1))

        resp = self.client.get(reverse("monitor-donations-stats-ajax"))
        self.assertEqual(resp.status_code, 200)
        d = resp.json()

        daily = d["daily"]
        self.assertEqual((daily["start"], daily["end"]), ("2026-02-14", "2026-03-15"))
        self.assertEqual(len(daily["data"]), 30)
        self.assertEqual(_pick(daily["data"][0], "day", "amount", "count"), ("2026-02-14", 2.25, 1))
        self.assertEqual(_pick(daily["data"][-1], "day", "amount", "count"), ("2026-03-15", 15.5, 2))
        self.assertAlmostEqual(sum(x["amount"] for x in daily["data"]), 17.75)

        monthly = d["monthly"]
        self.assertEqual((monthly["start"], monthly["end"]), ("2024-10-01", "2026-03-15"))
        self.assertEqual(len(monthly["data"]), 18)
        self.assertEqual(_pick(monthly["data"][0], "month", "amount"), ("2024-10", 7.0))
        self.assertEqual(_pick(monthly["data"][-2], "month", "amount"), ("2026-02", 102.25))
        self.assertEqual(_pick(monthly["data"][-1], "month", "amount"), ("2026-03", 15.5))
        self.assertAlmostEqual(sum(x["amount"] for x in monthly["data"]), 124.75)

        self.assertEqual(
            [_pick(x, "year", "amount") for x in d["yearly"]["data"]],
            [
                (2021, 3.0),
                (2022, 0.0),
                (2023, 0.0),
                (2024, 57.0),
                (2025, 0.0),
                (2026, 117.75),
            ],
        )

    def test_custom_range_applies_to_daily_and_monthly(self):
        self._donate("1.00", self._local_dt(2025, 12, 31, 23))
        self._donate("2.00", self._local_dt(2026, 1, 1, 0))
        self._donate("4.00", self._local_dt(2026, 2, 10))
        self._donate("8.00", self._local_dt(2026, 2, 11))

        resp = self.client.get(reverse("monitor-donations-stats-ajax"), {"start": "2026-01-01", "end": "2026-02-10"})
        self.assertEqual(resp.status_code, 200)
        d = resp.json()

        self.assertEqual((d["daily"]["start"], d["daily"]["end"]), ("2026-01-01", "2026-02-10"))
        self.assertEqual(len(d["daily"]["data"]), 41)
        self.assertEqual(_pick(d["daily"]["data"][0], "day", "amount"), ("2026-01-01", 2.0))
        self.assertEqual(_pick(d["daily"]["data"][-1], "day", "amount"), ("2026-02-10", 4.0))
        self.assertEqual((d["monthly"]["start"], d["monthly"]["end"]), ("2026-01-01", "2026-02-10"))
        self.assertEqual(
            [_pick(x, "month", "amount") for x in d["monthly"]["data"]], [("2026-01", 2.0), ("2026-02", 4.0)]
        )
        # Yearly ignores the range
        yearly = {x["year"]: x["amount"] for x in d["yearly"]["data"]}
        self.assertEqual(yearly[2025], 1.0)
        self.assertEqual(yearly[2026], 14.0)

    def test_no_donations(self):
        d = self.client.get(reverse("monitor-donations-stats-ajax")).json()
        self.assertEqual(len(d["daily"]["data"]), 30)
        self.assertTrue(all(x["amount"] == 0 for x in d["daily"]["data"]))
        self.assertEqual(len(d["monthly"]["data"]), 18)
        self.assertEqual(d["yearly"]["data"], [])

    def test_invalid_range(self):
        url = reverse("monitor-donations-stats-ajax")
        self.assertEqual(self.client.get(url, {"start": "not-a-date"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"start": "2026-02-01", "end": "2026-01-01"}).status_code, 400)

    def test_counts_medians_and_sources(self):
        self._donate("10.00", self._local_dt(2026, 1, 5), source="p")
        self._donate("20.00", self._local_dt(2026, 1, 6), source="s")
        self._donate("60.00", self._local_dt(2026, 2, 1), source="s")
        d = self.client.get(
            reverse("monitor-donations-stats-ajax"), {"start": "2026-01-01", "end": "2026-02-28"}
        ).json()
        self.assertEqual((d["daily"]["count"], d["daily"]["amount"], d["daily"]["median_amount"]), (3, 90.0, 20.0))
        january, february = d["monthly"]["data"]
        self.assertEqual(january["count"], 2)
        self.assertEqual(january["by_source"]["p"], {"amount": 10.0, "count": 1})
        self.assertEqual(january["by_source"]["s"], {"amount": 20.0, "count": 1})
        self.assertEqual(january["by_source"]["t"], {"amount": 0.0, "count": 0})
        self.assertEqual(february["by_source"]["s"], {"amount": 60.0, "count": 1})
        self.assertEqual(d["monthly"]["sources"], {"p": "paypal", "s": "stripe", "t": "transfer"})

    def test_period_donor_stats(self):
        uploader = User.objects.get(username="User2")
        uploader.profile.num_sounds = 3
        uploader.profile.save()
        # Returning donor (by user): previous donation before the period
        self._donate("5.00", self._local_dt(2025, 6, 1), user=uploader, email="a@example.com")
        self._donate("10.00", self._local_dt(2026, 1, 10), user=uploader, email="a@example.com")
        # Returning donor (by email, no account): previous donation in the period
        self._donate("20.00", self._local_dt(2026, 1, 1), email="b@example.com")
        self._donate("30.00", self._local_dt(2026, 1, 21), email="B@example.com")
        # First-time donor with an account who is not an uploader
        self._donate("100.00", self._local_dt(2026, 1, 15), user=self.user, email="c@example.com")

        period = self.client.get(
            reverse("monitor-donations-stats-ajax"), {"start": "2026-01-01", "end": "2026-01-31"}
        ).json()["period"]

        self.assertEqual(period["count"], 4)
        self.assertEqual(period["unique_donors"], 3)
        self.assertEqual(period["first_time"], {"count": 2, "amount": 120.0})
        self.assertEqual(period["returning"]["count"], 2)
        self.assertEqual(period["returning"]["amount"], 40.0)
        # 223 days (2025-06-01 to 2026-01-10) and 20 days -> median 121.5
        self.assertAlmostEqual(period["returning"]["median_days_since_previous"], 121.5, places=1)
        self.assertEqual(period["uploaders"]["uploaders"], {"count": 1, "amount": 10.0})
        self.assertEqual(period["uploaders"]["non_uploaders"], {"count": 1, "amount": 100.0})
        self.assertEqual(period["uploaders"]["no_account"], {"count": 2, "amount": 50.0})
        self.assertEqual(
            [(b["label"], b["count"]) for b in period["amount_distribution"]],
            [("< €5", 0), ("€5–10", 0), ("€10–20", 1), ("€20–50", 2), ("€50–100", 0), ("€100+", 1)],
        )

    def test_period_donation_requests(self):
        user2 = User.objects.get(username="User2")
        popup = DonationRequest.RequestType.AFTER_DOWNLOAD_POPUP
        email = DonationRequest.RequestType.EMAIL_REQUEST_MANY_DOWNLOADS
        # self.user: 3 popups before the first donation, 1 popup + 1 email between the first and the second
        for day in [1, 2, 3]:
            self._request(self.user, popup, self._local_dt(2026, 1, day))
        self._donate("10.00", self._local_dt(2026, 1, 5), user=self.user)
        self._request(self.user, popup, self._local_dt(2026, 1, 10))
        self._request(self.user, email, self._local_dt(2026, 1, 11))
        self._donate("10.00", self._local_dt(2026, 1, 20), user=self.user)
        # user2: 2 popups, no donation
        self._request(user2, popup, self._local_dt(2026, 1, 7))
        self._request(user2, popup, self._local_dt(2026, 1, 8))
        # Donation without an account is not included
        self._donate("10.00", self._local_dt(2026, 1, 25))

        period = self.client.get(
            reverse("monitor-donations-stats-ajax"), {"start": "2026-01-01", "end": "2026-01-31"}
        ).json()["period"]

        before = period["requests_before_donation"]
        self.assertEqual((before["donations_included"], before["donations_total"]), (2, 3))
        by_type = {t["type"]: t for t in before["by_type"]}
        self.assertEqual(by_type[popup]["donations_with_requests"], 2)
        self.assertEqual(by_type[popup]["percentage_with_requests"], 100.0)
        self.assertEqual(by_type[popup]["average_requests"], 2.0)  # (3 + 1) / 2
        self.assertEqual(by_type[email]["donations_with_requests"], 1)
        self.assertEqual(by_type[email]["percentage_with_requests"], 50.0)
        self.assertEqual(by_type[email]["average_requests"], 1.0)

        conversion = {t["type"]: t for t in period["request_conversion"]}
        self.assertEqual(conversion[popup]["requests"], 6)
        self.assertEqual(conversion[popup]["converted_requests"], 4)
        self.assertEqual((conversion[popup]["users"], conversion[popup]["converted_users"]), (2, 1))
        self.assertEqual(conversion[popup]["user_conversion_rate"], 50.0)
        self.assertEqual(conversion[email]["converted_requests"], 1)
        self.assertIsNone(conversion[DonationRequest.RequestType.EMAIL_REMINDER_REPEAT_DONATION]["conversion_rate"])

    @mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2026, 7, 15))
    def test_yearly_projection_with_monthly_distribution(self, _):
        self._donate("500.00", self._local_dt(2022, 11, 1))  # First year, not used for the distribution
        for year in [2023, 2024, 2025]:
            self._donate("60.00", self._local_dt(year, 1, 10))
            self._donate("40.00", self._local_dt(year, 7, 20))
        self._donate("60.00", self._local_dt(2026, 1, 10))
        self._donate("10.00", self._local_dt(2026, 7, 2))

        projection = self.client.get(reverse("monitor-donations-stats-ajax")).json()["yearly"]["projection"]

        elapsed_share = 0.6 + 0.4 * 15 / 31
        self.assertEqual(projection["year"], 2026)
        self.assertEqual(projection["method"], "monthly_distribution")
        self.assertEqual(projection["years_used"], [2023, 2024, 2025])
        self.assertEqual(projection["amount_so_far"], 70.0)
        self.assertAlmostEqual(projection["elapsed_share"], elapsed_share)
        self.assertAlmostEqual(projection["projected_total"], 70 / elapsed_share)
        self.assertAlmostEqual(projection["remaining"], 70 / elapsed_share - 70)

    @mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2026, 7, 15))
    def test_yearly_projection_without_past_years(self, _):
        self._donate("98.00", self._local_dt(2026, 3, 1))
        projection = self.client.get(reverse("monitor-donations-stats-ajax")).json()["yearly"]["projection"]
        self.assertEqual(projection["method"], "days_elapsed")
        self.assertAlmostEqual(projection["elapsed_share"], 196 / 365)
        self.assertAlmostEqual(projection["projected_total"], 98 * 365 / 196)

    @mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2026, 7, 15))
    def test_yearly_projection_without_donations_this_year(self, _):
        self._donate("10.00", self._local_dt(2025, 3, 1))
        self.assertIsNone(self.client.get(reverse("monitor-donations-stats-ajax")).json()["yearly"]["projection"])

    def _mock_now(self, *args):
        now = timezone.make_aware(datetime.datetime(*args))
        return (
            mock.patch("django.utils.timezone.now", return_value=now),
            mock.patch("django.utils.timezone.localdate", return_value=now.date()),
        )

    def _get_with_now(self, now_args, params=None):
        patch_now, patch_localdate = self._mock_now(*now_args)
        with patch_now, patch_localdate:
            return self.client.get(reverse("monitor-donations-stats-ajax"), params or {}).json()

    def test_daily_projection_with_past_distribution(self):
        # In the past days, 30% of the donations arrived before 12:00
        for day in [10, 11, 12]:
            self._donate("3.00", self._local_dt(2026, 7, day, 9))
            self._donate("7.00", self._local_dt(2026, 7, day, 18))
        self._donate("6.00", self._local_dt(2026, 7, 15, 8))
        projection = self._get_with_now((2026, 7, 15, 12))["daily"]["projection"]
        self.assertEqual(projection["label"], "2026-07-15")
        self.assertEqual(projection["method"], "past_distribution")
        self.assertEqual(projection["past_periods_used"], 90)
        self.assertAlmostEqual(projection["elapsed_share"], 0.3)
        self.assertAlmostEqual(projection["projected_total"], 20.0)
        self.assertAlmostEqual(projection["remaining"], 14.0)
        self.assertAlmostEqual(projection["projected_count"], 1 / 0.3)

    def test_daily_projection_without_past_donations(self):
        self._donate("6.00", self._local_dt(2026, 7, 15, 8))
        projection = self._get_with_now((2026, 7, 15, 6))["daily"]["projection"]
        self.assertEqual(projection["method"], "time_elapsed")
        self.assertAlmostEqual(projection["elapsed_share"], 0.25)
        self.assertAlmostEqual(projection["projected_total"], 24.0)

    def test_monthly_projection_with_past_distribution(self):
        # In the past months, 40% of the donations arrived in the first half of the month
        for month in [4, 5, 6]:
            self._donate("4.00", self._local_dt(2026, month, 3))
            self._donate("6.00", self._local_dt(2026, month, 25))
        self._donate("8.00", self._local_dt(2026, 7, 2))
        # 2026-07-16 12:00 is halfway through July
        projection = self._get_with_now((2026, 7, 16, 12))["monthly"]["projection"]
        self.assertEqual(projection["label"], "2026-07")
        self.assertEqual(projection["method"], "past_distribution")
        self.assertEqual(projection["past_periods_used"], 12)
        self.assertAlmostEqual(projection["elapsed_share"], 0.4)
        self.assertAlmostEqual(projection["projected_total"], 20.0)
        self.assertAlmostEqual(projection["remaining_count"], 1 / 0.4 - 1)

    def test_no_daily_and_monthly_projection_for_past_ranges_or_without_donations(self):
        self._donate("8.00", self._local_dt(2026, 6, 2))
        d = self._get_with_now((2026, 7, 16, 12), {"start": "2026-06-01", "end": "2026-06-30"})
        self.assertIsNone(d["daily"]["projection"])
        self.assertIsNone(d["monthly"]["projection"])
        # No donations today or this month yet
        d = self._get_with_now((2026, 7, 16, 12))
        self.assertIsNone(d["daily"]["projection"])
        self.assertIsNone(d["monthly"]["projection"])

    def test_recurrent_donors(self):
        # Monthly donor (by email), still active: 5 donations, 4 of them in the period
        for month in [1, 2, 3, 4, 5]:
            self._donate("5.00", self._local_dt(2026, month, 3 + month % 2), email="monthly@example.com")
        # Yearly donor (by user) whose series stopped (no donation in 2025 or later): one donation in the period
        for year in [2022, 2023, 2024]:
            self._donate("50.00", self._local_dt(year, 2, 1), user=self.user, email="yearly@example.com")
        self._donate("20.00", self._local_dt(2024, 2, 20), email="other@example.com")
        # Irregular donor
        for date in [(2024, 1, 1), (2024, 2, 1), (2024, 6, 1)]:
            self._donate("10.00", self._local_dt(*date), email="irregular@example.com")
        # Two donations only: not enough to be recurrent
        self._donate("7.00", self._local_dt(2024, 1, 15), email="twice@example.com")
        self._donate("7.00", self._local_dt(2024, 2, 15), email="twice@example.com")

        d = self._get_with_now((2026, 5, 20, 12), {"start": "2024-02-01", "end": "2026-05-20"})
        recurrent = d["period"]["recurrent"]

        # In the period: 5 monthly + 1 yearly (2024) recurrent; other@, irregular (2), twice (1) not recurrent
        self.assertEqual(d["period"]["count"], 10)
        self.assertEqual(recurrent["donations"], 6)
        self.assertEqual(recurrent["amount"], 75.0)
        self.assertEqual((recurrent["donors"], recurrent["series"]), (2, 2))
        self.assertEqual(recurrent["average_amount"], 12.5)
        self.assertEqual(recurrent["median_amount"], 5.0)
        self.assertEqual(recurrent["non_recurrent_average_amount"], (20 + 10 + 10 + 7) / 4)
        self.assertEqual(recurrent["average_series_donations"], 4.0)
        self.assertEqual(recurrent["average_series_amount"], (25 + 150) / 2)
        # Monthly series is on time (last donation on 2026-05-04), yearly one is overdue
        self.assertEqual(recurrent["stopped_series"], 1)
        cadences = {c["label"]: c for c in recurrent["by_cadence"]}
        self.assertEqual(set(cadences), {"Monthly", "Yearly"})
        self.assertEqual((cadences["Monthly"]["donors"], cadences["Monthly"]["donations"]), (1, 5))
        self.assertEqual(cadences["Monthly"]["amount"], 25.0)
        self.assertEqual((cadences["Yearly"]["donors"], cadences["Yearly"]["donations"]), (1, 1))


class RecurrentSeriesTestCase(TestCase):
    def _times(self, *days):
        start = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        return [start + datetime.timedelta(days=d) for d in days]

    def test_find_series(self):
        find = donations_stats._find_recurrent_series
        self.assertEqual(find(self._times(0, 30)), [])
        self.assertEqual(find(self._times(0, 30, 61, 90)), [(0, 3, 30.0)])
        # Irregular intervals
        self.assertEqual(find(self._times(0, 30, 120, 130)), [])
        # Irregular donation before a series and a pause between two series
        series = find(self._times(0, 100, 130, 160, 190, 700, 1065, 1430))
        self.assertEqual([(a, b) for a, b, _ in series], [(1, 4), (5, 7)])
        self.assertAlmostEqual(series[1][2], 365.0)
        # Duplicated donations (same day) break series
        self.assertEqual(find(self._times(0, 0, 0, 0)), [])
