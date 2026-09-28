import pytest
from django.core.cache import cache, caches
from django.test import RequestFactory

from utils.download_limit import (
    DownloadType,
    count_download_and_set_sentinel,
    download_limit_reached,
    download_limit_reached_response,
    get_daily_download_count,
    increment_daily_download_count,
    is_new_download,
    new_download_blocked,
)
from utils.ratelimit import request_limit_events_total
from utils.test_helpers import counter_samples

pytestmark = pytest.mark.redis


@pytest.fixture
def abuse_redis():
    """The abuse cache's raw redis client, flushed so counters start from a clean slate."""
    client = caches["abuse"]._cache.get_client(write=True)
    client.flushdb()
    return client


def test_count_starts_at_zero(abuse_redis):
    assert get_daily_download_count(123) == 0


def test_increment_counts_up_and_is_readable(abuse_redis):
    assert increment_daily_download_count(123) == 1
    assert increment_daily_download_count(123) == 2
    assert get_daily_download_count(123) == 2


def test_counts_are_per_user(abuse_redis):
    increment_daily_download_count(123)
    assert get_daily_download_count(456) == 0


def test_increment_sets_ttl(abuse_redis):
    increment_daily_download_count(123)
    key = next(iter(abuse_redis.scan_iter("downloadlimit:123:*")))
    assert abuse_redis.ttl(key) > 0


def test_limit_reached_at_threshold(abuse_redis, settings):
    settings.MAX_DOWNLOADS_PER_DAY = 2
    increment_daily_download_count(123)
    assert not download_limit_reached(123)
    increment_daily_download_count(123)
    assert download_limit_reached(123)


def _daily_download_limit_events():
    samples = counter_samples(request_limit_events_total, "reason", "enforced", "user_type")
    return samples.get(("daily_download_limit", "true", "authenticated"), 0)


@pytest.mark.django_db
def test_reached_response_returns_429_and_counts_event(django_user_model):
    # download_limit_reached_response is the shared 429 helper that every over-limit download
    # type funnels through; assert it emits the request-limit event once with the right labels.
    request = RequestFactory().get("/people/user/sounds/1/download/")
    request.user = django_user_model.objects.create_user("u")
    before = _daily_download_limit_events()

    response = download_limit_reached_response(request)

    assert response.status_code == 429
    assert _daily_download_limit_events() == before + 1


def test_fails_open_when_redis_unavailable(settings):
    settings.CACHES = {
        **settings.CACHES,
        "abuse": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            # Invalid location, will cause a ConnectionError
            "LOCATION": "redis://localhost:1/0",
        },
    }
    assert get_daily_download_count(123) == 0
    assert increment_daily_download_count(123) == 0
    assert not download_limit_reached(123)


@pytest.fixture
def request_with_user(abuse_redis, db, django_user_model):
    cache.clear()
    request = RequestFactory().get("/")
    request.user = django_user_model.objects.create_user("downloader")
    return request


def test_is_new_download_true_without_sentinel(request_with_user):
    assert is_new_download(request_with_user, DownloadType.SOUND, 1)


def test_is_new_download_false_with_sentinel(request_with_user):
    cache.set("sdwn_1_%d" % request_with_user.user.id, True, 60)
    assert not is_new_download(request_with_user, DownloadType.SOUND, 1)


def test_new_download_blocked_only_when_new_and_over_limit(request_with_user, settings):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    assert not new_download_blocked(request_with_user, DownloadType.SOUND, 1)
    increment_daily_download_count(request_with_user.user.id)
    assert new_download_blocked(request_with_user, DownloadType.SOUND, 1)


def test_new_download_blocked_false_for_continuation_even_over_limit(request_with_user, settings):
    # A download already in progress (sentinel set) is never blocked, even over the limit.
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(request_with_user.user.id)
    cache.set("sdwn_1_%d" % request_with_user.user.id, True, 60)
    assert not new_download_blocked(request_with_user, DownloadType.SOUND, 1)


def test_count_download_and_set_sentinel_first_call_counts_and_sets_sentinel(
    request_with_user, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        result = count_download_and_set_sentinel(request_with_user, DownloadType.SOUND, 1)
    assert result is True
    assert get_daily_download_count(request_with_user.user.id) == 1
    assert cache.get("sdwn_1_%d" % request_with_user.user.id) is True


def test_count_download_and_set_sentinel_repeat_call_does_not_recount(
    request_with_user, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        count_download_and_set_sentinel(request_with_user, DownloadType.SOUND, 1)
    with django_capture_on_commit_callbacks(execute=True):
        result = count_download_and_set_sentinel(request_with_user, DownloadType.SOUND, 1)
    assert result is False
    assert get_daily_download_count(request_with_user.user.id) == 1
