from unittest import mock

import pytest

from utils.search_logging import SearchArchiveHandler, archive_search, logger


def test_disabled_does_not_construct_event(settings):
    settings.SEARCH_ARCHIVE_ENABLED = False
    params = mock.Mock()
    archive_search(source="web", params=params, num_results=0, query_time=None, ip=None, user_id=None)
    params.items.assert_not_called()


def test_send_failure_is_contained(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch("utils.search_logging.socket.socket") as factory:
        handler = SearchArchiveHandler()
        factory.return_value.sendto.side_effect = OSError
        with mock.patch.object(logger, "handlers", [handler]):
            archive_search(source="web", params={"q": "rain"}, num_results=0, query_time=None, ip=None, user_id=None)
        factory.return_value.sendto.assert_called_once()
        handler.close()


def test_oversized_parameter_is_dropped(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch.object(logger, "info") as emit:
        archive_search(source="web", params={"q": "x" * 4097}, num_results=0, query_time=None, ip=None, user_id=None)
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
            user_id=None,
        )
    assert emit.call_args.args[0]["params"] == {"q": "rain", "si_tags": "1", "si_name": "on"}


def test_encoded_datagram_size_limit(settings):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch("utils.search_logging.socket.socket") as factory:
        handler = SearchArchiveHandler()
        with mock.patch.object(logger, "handlers", [handler]):
            archive_search(
                source="web",
                params={"q": "x" * 4096, "f": "x" * 4096},
                num_results=0,
                query_time=None,
                ip=None,
                user_id=None,
            )
        factory.return_value.sendto.assert_not_called()
        handler.close()


@pytest.mark.parametrize("user_id", [42, None])
def test_user_id_is_sent(settings, user_id):
    settings.SEARCH_ARCHIVE_ENABLED = True
    with mock.patch.object(logger, "info") as emit:
        archive_search(source="web", params={"q": "rain"}, num_results=0, query_time=None, ip=None, user_id=user_id)
    assert emit.call_args.args[0]["user_id"] == user_id


def _web_search_event(client):
    from django.urls import reverse

    from utils.pagination import PreSlicedCountProvidedPaginator
    from utils.search import SearchResults

    results = SearchResults(docs=[], num_found=0, q_time=3)
    paginator = PreSlicedCountProvidedPaginator([], 15, 0)
    with (
        mock.patch("search.views.perform_search_engine_query", return_value=(results, paginator)),
        mock.patch.object(logger, "info") as emit,
    ):
        response = client.get(reverse("sounds-search") + "?q=rain")
    assert response.status_code == 200
    return emit.call_args.args[0]


@pytest.mark.django_db
def test_web_sends_user_id_for_logged_in_and_anonymous_users(client, settings, django_user_model):
    settings.SEARCH_ARCHIVE_ENABLED = True
    assert _web_search_event(client)["user_id"] is None
    user = django_user_model.objects.create_user(username="archive-web-test")
    client.force_login(user)
    assert _web_search_event(client)["user_id"] == user.id


@pytest.mark.django_db
def test_web_emits_archive_event(client, settings):
    from django.urls import reverse

    from utils.pagination import PreSlicedCountProvidedPaginator
    from utils.search import SearchResults

    settings.SEARCH_ARCHIVE_ENABLED = True
    results = SearchResults(docs=[], num_found=0, q_time=3)
    paginator = PreSlicedCountProvidedPaginator([], 15, 0)
    with (
        mock.patch("search.views.perform_search_engine_query", return_value=(results, paginator)),
        mock.patch.object(logger, "info") as emit,
    ):
        response = client.get(reverse("sounds-search") + "?q=rain")
    assert response.status_code == 200
    assert emit.call_args.args[0]["source"] == "web"
    assert emit.call_args.args[0]["query_time_ms"] == 3
    assert emit.call_args.args[0]["params"] == {"q": "rain"}


@pytest.mark.django_db
def test_api_emits_archive_event(client, settings, django_user_model):
    from django.urls import reverse

    settings.SEARCH_ARCHIVE_ENABLED = True
    user = django_user_model.objects.create_user(username="archive-api-test")
    client.force_login(user)
    with (
        mock.patch("apiv2.views.api_search", return_value=([], 0, -1, None, None, None, None, None, None)),
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
        assert payload["user_id"] == user.id
