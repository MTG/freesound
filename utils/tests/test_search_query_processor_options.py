from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from utils.search import search_query_processor, search_query_processor_options


class SearchQueryProcessorOptionsTest(TestCase):
    def test_search_option_int(self):
        request = RequestFactory().get("/?test=1")
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)

        option = search_query_processor_options.SearchOptionInt(query_param_name="test")
        option.set_search_query_processor(sqp)
        assert option.get_value_from_request() == 1

    def test_search_option_int_bad_type(self):
        request = RequestFactory().get("/?test=not_an_int")
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)

        option = search_query_processor_options.SearchOptionInt(query_param_name="test")
        option.set_search_query_processor(sqp)
        assert option.get_value_from_request() is None


class PageOptionTest(TestCase):
    def _value_to_apply(self, query):
        request = RequestFactory().get(query)
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)
        return sqp.get_option_value_to_apply("page")

    def test_page_zero_clamps_to_1(self):
        assert self._value_to_apply("/?page=0") == 1

    def test_page_negative_clamps_to_1(self):
        assert self._value_to_apply("/?page=-3") == 1

    def test_page_normal_value_passes_through(self):
        assert self._value_to_apply("/?page=4") == 4

    def test_page_non_numeric_defaults_to_1(self):
        assert self._value_to_apply("/?page=abc") == 1


class DisplayMapModeTest(TestCase):
    def test_display_map_mode(self):
        request = RequestFactory().get("/?mm=1")
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)
        assert sqp.get_option_value_to_apply("display_as_packs") is False

    def test_display_map_mode_and_display_as_packs(self):
        request = RequestFactory().get("/?mm=1&dp=1")
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)
        assert sqp.get_option_value_to_apply("display_as_packs") is False

    def test_display_map_mode_and_display_as_packs_and_grouping_pack(self):
        request = RequestFactory().get("/?mm=1&dp=1&pack_grouping=1")
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)
        assert sqp.get_option_value_to_apply("display_as_packs") is False
