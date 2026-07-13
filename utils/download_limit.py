import datetime
import enum
import logging

from django.conf import settings
from django.core.cache import cache, caches
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger("web")

DOWNLOAD_LIMIT_CACHE_ALIAS = "abuse"
DOWNLOAD_LIMIT_KEY_PREFIX = "downloadlimit"
DOWNLOAD_LIMIT_KEY_TTL = 60 * 60 * 48  # 48 hours

# TTL of the per-download "in progress" sentinel (see count_download_and_set_sentinel). Long enough to
# span a single (possibly multi-part / slow) download; short enough that it doesn't persist
# between genuinely separate downloads of the same object.
DOWNLOAD_LIMIT_SENTINEL_TTL = 60 * 5  # 5 minutes


def _get_redis_client():
    # Native redis-py client from the cache backend. We use the raw client so a single
    # pipelined INCR+EXPIRE creates-and-bumps in one round-trip (the backend's incr()
    # would raise on a missing key).
    return caches[DOWNLOAD_LIMIT_CACHE_ALIAS]._cache.get_client(write=True)


def _daily_key(user_id):
    today = datetime.datetime.now(datetime.timezone.utc).date()
    return f"{DOWNLOAD_LIMIT_KEY_PREFIX}:{user_id}:{today:%Y%m%d}"


def get_daily_download_count(user_id):
    try:
        value = _get_redis_client().get(_daily_key(user_id))
        return int(value) if value is not None else 0
    except Exception:  # noqa
        # Intentionally fail open on redis error
        logger.warning("Could not read daily download count for user %s", user_id, exc_info=True)
        return 0


def increment_daily_download_count(user_id):
    """Increment the number of downloads for a user. Use the underlying redis client in order
    to increment in 1 request (creates and sets to 1 if it doesn't yet exist) and set a 2 day
    expiry."""
    try:
        client = _get_redis_client()
        key = _daily_key(user_id)
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, DOWNLOAD_LIMIT_KEY_TTL)
        count, _ = pipe.execute()
        return int(count)
    except Exception:  # noqa
        # Intentionally fail open on redis error
        logger.warning("Could not increment daily download count for user %s", user_id, exc_info=True)
        return 0


def download_limit_reached(user_id):
    return get_daily_download_count(user_id) >= settings.MAX_DOWNLOADS_PER_DAY


def user_download_limit_reached(request):
    """Whether the request's user is over the daily download limit."""
    return request.user.is_authenticated and download_limit_reached(request.user.id)


class DownloadType(enum.Enum):
    """Something that can be downloaded; values are used in the redis download sentinel check."""

    SOUND = "sdwn"
    PACK = "pdwn"
    BOOKMARK_CATEGORY = "bdwn"
    COLLECTION = "cdwn"


def _sentinel_key(download_type: DownloadType, object_id: int, user_id: int) -> str:
    return f"{download_type.value}_{object_id}_{user_id}"


def download_limit_reached_response(request: HttpRequest) -> HttpResponse:
    """The 429 page returned when ``new_download_blocked`` says a download must not start."""
    return render(
        request, "sounds/download_limit_reached.html", {"message": settings.DOWNLOAD_LIMIT_MESSAGE}, status=429
    )


def new_download_blocked(request: HttpRequest, download_type: DownloadType, object_id: int) -> bool:
    """Check if the user is allowed to download this item.

    The download is blocked if it's a new download and if the user is over their daily limit.
    see ``count_download_and_set_sentinel`` for a description of what new download means.
    """
    is_new_download = cache.get(_sentinel_key(download_type, object_id, request.user.id), None) is None
    return is_new_download and download_limit_reached(request.user.id)


def count_download_and_set_sentinel(request: HttpRequest, download_type: DownloadType, object_id: int) -> bool:
    """Count this download towards the user's daily limit and mark it as in progress.

    We mark a 5 minute sentinel when a user downloads something for the first time. This guards
    us from double-counting downloads if the user's browser or download manager makes multiple
    requests to download a single file.
    We've seen that sometimes a client makes a request to get the content-length and then makes
    another request with a Range header. In this case we don't want to save multiple
    Download rows to the database or count this download multiple times in our abuse counter.

    Increments the daily download count if this is a new download and increments the
    "existing download" sentinel key every time this is called, new or not.

    Returns True if this is a new download, False otherwise.
    """
    user_id = request.user.id
    sentinel_key = _sentinel_key(download_type, object_id, user_id)
    is_new_download = cache.get(sentinel_key, None) is None
    if is_new_download:
        transaction.on_commit(lambda: increment_daily_download_count(user_id))
    transaction.on_commit(lambda: cache.set(sentinel_key, True, DOWNLOAD_LIMIT_SENTINEL_TTL))
    return is_new_download
