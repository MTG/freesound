import pytest
from django.core.cache import caches
from django.test import RequestFactory

from utils.download_limit import (
    download_limit_reached,
    download_limit_reached_response,
    get_daily_download_count,
    increment_daily_download_count,
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
