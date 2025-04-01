from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from utils.search import search_query_processor_options, search_query_processor


class SearchQueryProcessorOptionsTest(TestCase):
    def test_search_option_int(self):
        request = RequestFactory().get('/?test=1')
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)

        option = search_query_processor_options.SearchOptionInt(query_param_name='test')
        option.set_search_query_processor(sqp)
        assert option.get_value_from_request() == 1

    def test_search_option_int_bad_type(self):
        request = RequestFactory().get('/?test=not_an_int')
        request.user = AnonymousUser()
        sqp = search_query_processor.SearchQueryProcessor(request)

        option = search_query_processor_options.SearchOptionInt(query_param_name='test')
        option.set_search_query_processor(sqp)
        assert option.get_value_from_request() is None
