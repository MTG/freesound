from unittest import mock

import pytest

from utils.search_logging import SearchArchiveHandler, archive_search, logger


def test_disabled_does_not_construct_event(settings):
    settings.SEARCH_ARCHIVE_ENABLED = False
    params = mock.Mock()
    archive_search(source="web", params=params, num_results=0, query_time=None, ip=None)
    params.items.assert_not_called()


def test_send_failure_is_contained(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch("utils.search_logging.socket.socket") as factory:
        handler = SearchArchiveHandler()
        factory.return_value.sendto.side_effect = OSError
        with mock.patch.object(logger, "handlers", [handler]):
            archive_search(source="web", params={"q": "rain"}, num_results=0, query_time=None, ip=None)
        factory.return_value.sendto.assert_called_once()
        handler.close()


def test_oversized_parameter_is_dropped(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch.object(logger, "info") as emit:
        archive_search(source="web", params={"q": "x" * 4097}, num_results=0, query_time=None, ip=None)
    emit.assert_not_called()


def test_archive_search_filters_parameters(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch.object(logger, "info") as emit:
        archive_search(
            source="web",
            params={"q": "rain", "si_tags": "1", "si_name": "on", "si0": "tags", "token": "secret", "st": "[1,2]"},
            num_results=0,
            query_time=None,
            ip=None,
        )
    assert emit.call_args.args[0]["params"] == {"q": "rain", "si_tags": "1", "si_name": "on"}


def test_encoded_datagram_size_limit(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch("utils.search_logging.socket.socket") as factory:
        handler = SearchArchiveHandler()
        with mock.patch.object(logger, "handlers", [handler]):
            archive_search(
                source="web", params={"q": "x" * 4096, "f": "x" * 4096}, num_results=0, query_time=None, ip=None
            )
        factory.return_value.sendto.assert_not_called()
        handler.close()


@pytest.mark.django_db
def test_web_emits_with_redis_disabled(client, settings):
    from django.urls import reverse

    from utils.pagination import PreSlicedCountProvidedPaginator
    from utils.search import SearchResults

    settings.SEARCH_ARCHIVE_ENABLED = True
    settings.SEARCH_SAVE_QUERY_RECORDS = False
    results = SearchResults(docs=[], num_found=0, q_time=3)
    paginator = PreSlicedCountProvidedPaginator([], 15, 0)
    with (
        mock.patch("search.views.perform_search_engine_query", return_value=(results, paginator)),
        mock.patch("search.views.save_record_of_search_query") as redis,
        mock.patch.object(logger, "info") as emit,
    ):
        response = client.get(reverse("sounds-search") + "?q=rain")
    assert response.status_code == 200
    redis.assert_not_called()
    assert emit.call_args.args[0]["source"] == "web"
    assert emit.call_args.args[0]["query_time_ms"] == 3
    assert emit.call_args.args[0]["params"] == {"q": "rain"}


@pytest.mark.django_db
def test_api_emits_with_redis_disabled(client, settings, django_user_model):
    from django.urls import reverse

    settings.SEARCH_ARCHIVE_ENABLED = True
    settings.SEARCH_SAVE_QUERY_RECORDS = False
    user = django_user_model.objects.create_user(username="archive-api-test")
    client.force_login(user)
    with (
        mock.patch("apiv2.views.api_search", return_value=([], 0, -1, None, None, None, None, None, None)),
        mock.patch("apiv2.views.save_record_of_search_query") as redis,
        mock.patch.object(logger, "info") as emit,
    ):
        response = client.get(reverse("apiv2-sound-search") + "?query=rain&similar_to=%5B1,2%5D")
        assert response.status_code == 200
        payload = emit.call_args.args[0]
        assert payload["source"] == "api"
        assert payload["num_results"] == -1
        assert payload["query_time_ms"] is None
        assert payload["params"]["query"] == "rain"
        assert "similar_to" not in payload["params"]
        redis.assert_not_called()
