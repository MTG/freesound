import pytest
from django.core.cache import caches

from utils.download_limit import (
    download_limit_reached,
    get_daily_download_count,
    increment_daily_download_count,
)

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
