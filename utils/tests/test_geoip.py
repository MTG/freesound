from unittest import mock

from django.test import SimpleTestCase, override_settings

from utils import geoip


class FakeReader:
    def __init__(self, records):
        self.records = records

    def get(self, ip):
        return self.records.get(ip)

    def close(self):
        pass


class GetCountryIsoCodeTest(SimpleTestCase):
    def lookup(self, ip, records):
        with mock.patch("utils.geoip._get_reader", return_value=FakeReader(records)):
            return geoip.get_country_iso_code(ip)

    def test_returns_country_code(self):
        self.assertEqual(self.lookup("5.6.7.8", {"5.6.7.8": {"country": {"iso_code": "ES"}}}), "ES")

    def test_ipv4_mapped_ipv6_is_looked_up_as_ipv4(self):
        self.assertEqual(self.lookup("::ffff:5.6.7.8", {"5.6.7.8": {"country": {"iso_code": "ES"}}}), "ES")

    def test_unknown_or_invalid_values_return_empty(self):
        self.assertEqual(self.lookup("5.6.7.8", {}), "")
        self.assertEqual(self.lookup("5.6.7.8", {"5.6.7.8": {"continent": {"code": "EU"}}}), "")
        self.assertEqual(self.lookup("5.6.7.8", {"5.6.7.8": {"country": {"iso_code": "es"}}}), "")
        for ip in ("-", "", None, "not-an-ip"):
            self.assertEqual(self.lookup(ip, {}), "")

    def test_lookup_error_returns_empty(self):
        reader = mock.Mock(get=mock.Mock(side_effect=ValueError))
        with mock.patch("utils.geoip._get_reader", return_value=reader):
            self.assertEqual(geoip.get_country_iso_code("5.6.7.8"), "")

    @override_settings(GEOIP_COUNTRY_DATABASE_PATH="/nonexistent/GeoLite2-Country.mmdb")
    def test_missing_database_returns_empty(self):
        self.assertEqual(geoip.get_country_iso_code("5.6.7.8"), "")
