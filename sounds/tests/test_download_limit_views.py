from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core.cache import cache, caches
from django.core.management import call_command
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.text import slugify
from pytest_django.asserts import assertContains, assertNotContains

from bookmarks.models import Bookmark, BookmarkCategory
from fscollections.models import Collection, CollectionDownload, CollectionSound
from sounds.models import Download, PackDownload
from utils.download_limit import get_daily_download_count, increment_daily_download_count
from utils.ratelimit import request_limit_events_total
from utils.test_helpers import counter_samples, create_user_and_sounds

pytestmark = pytest.mark.redis


def _daily_download_limit_events():
    samples = counter_samples(request_limit_events_total, "reason", "enforced", "user_type")
    return samples.get(("daily_download_limit", "true", "authenticated"), 0)


@pytest.fixture
def limit_test_data(db):
    """Load users and clear abuse db on each call"""
    caches["abuse"]._cache.get_client(write=True).flushdb()
    cache.clear()
    call_command("loaddata", "licenses", "users")


@pytest.fixture
def uploader(limit_test_data):
    return User.objects.get(username="User2")


@pytest.fixture
def downloader(limit_test_data, client):
    user = User.objects.get(username="User1")
    client.force_login(user)
    return user


@pytest.fixture
def moderators_group(db):
    Group.objects.get_or_create(name="moderators")


@pytest.fixture
def download_sound(uploader):
    _, _, sounds = create_user_and_sounds(num_sounds=1, processing_state="OK", moderation_state="OK", user=uploader)
    return sounds[0]


@pytest.fixture
def download_pack(uploader):
    _, packs, _ = create_user_and_sounds(
        num_sounds=1, num_packs=1, processing_state="OK", moderation_state="OK", user=uploader
    )
    pack = packs[0]
    pack.process()
    return pack


@pytest.fixture
def sound_download_url(download_sound):
    return reverse("sound-download", args=[download_sound.user.username, download_sound.id])


@pytest.fixture
def download_collection(downloader, download_sound):
    collection = Collection.objects.create(user=downloader, name="limit collection")
    CollectionSound.objects.create(user=downloader, sound=download_sound, collection=collection, status="OK")
    return collection


@pytest.fixture
def bookmark_category(downloader, download_sound):
    category = BookmarkCategory.objects.create(user=downloader, name="limit bookmarks")
    Bookmark.objects.create(user=downloader, category=category, sound=download_sound)
    return category


@pytest.fixture
def public_collection(downloader, download_sound):
    collection = Collection.objects.create(user=downloader, name="render test collection", public=True)
    CollectionSound.objects.create(user=downloader, sound=download_sound, collection=collection, status="OK")
    return collection


def test_sound_download_under_limit_records_and_increments(
    client, settings, download_sound, downloader, sound_download_url, django_capture_on_commit_callbacks
):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    with mock.patch("sounds.views.sendfile", return_value=HttpResponse()):
        with django_capture_on_commit_callbacks(execute=True):
            response = client.get(sound_download_url)
    assert response.status_code == 200
    assert Download.objects.filter(user=downloader).count() == 1
    assert get_daily_download_count(downloader.id) == 1


def test_sound_download_over_limit_returns_429_and_no_row(
    client, settings, download_sound, downloader, sound_download_url
):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(downloader.id)
    response = client.get(sound_download_url)
    assert response.status_code == 429
    assert Download.objects.filter(user=downloader).count() == 0
    assert get_daily_download_count(downloader.id) == 1


def test_sound_download_error_does_not_increment(
    client, settings, download_sound, downloader, sound_download_url, django_capture_on_commit_callbacks
):
    # Simulate a download error - no daily download count and now Download row.
    settings.MAX_DOWNLOADS_PER_DAY = 200
    with mock.patch("sounds.views.sendfile", side_effect=Http404):
        with django_capture_on_commit_callbacks(execute=True):
            response = client.get(sound_download_url)
    assert response.status_code == 404
    assert Download.objects.filter(user=downloader).count() == 0
    assert get_daily_download_count(downloader.id) == 0
    assert cache.get("sdwn_%s_%d" % (download_sound.id, downloader.id), None) is None


def test_sound_download_over_limit_range_continuation_is_served(
    client, settings, download_sound, downloader, sound_download_url
):
    # User is over the limit but downloading a sound that has already been started.
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(downloader.id)
    cache.set("sdwn_%s_%d" % (download_sound.id, downloader.id), True, 60 * 5)
    before = _daily_download_limit_events()
    with mock.patch("sounds.views.sendfile", return_value=HttpResponse()):
        response = client.get(sound_download_url, HTTP_RANGE="bytes=0-")
    assert response.status_code == 200
    assert _daily_download_limit_events() == before


def test_sound_download_continuation_refreshes_sentinel_without_recounting(
    client, settings, download_sound, downloader, sound_download_url, django_capture_on_commit_callbacks
):
    # An in-progress download (sentinel present) refreshes its marker on every request and
    # does not re-count.
    settings.MAX_DOWNLOADS_PER_DAY = 200
    cache.set("sdwn_%s_%d" % (download_sound.id, downloader.id), True, 60 * 5)
    with mock.patch("sounds.views.sendfile", return_value=HttpResponse()):
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            client.get(sound_download_url, HTTP_RANGE="bytes=100-")
    assert len(callbacks) == 1
    assert Download.objects.filter(user=downloader).count() == 0
    assert get_daily_download_count(downloader.id) == 0


def test_pack_download_over_limit_returns_429_and_no_row(client, settings, download_pack, downloader):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(downloader.id)
    response = client.get(reverse("pack-download", args=[download_pack.user.username, download_pack.id]))
    assert response.status_code == 429
    assert PackDownload.objects.filter(user=downloader).count() == 0


def test_collection_download_over_limit_returns_429_and_no_row(client, settings, download_collection, downloader):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(downloader.id)
    url = reverse("download-collection", args=[download_collection.id, slugify(download_collection.name)])
    response = client.get(url)
    assert response.status_code == 429
    assert CollectionDownload.objects.filter(user=downloader).count() == 0


def test_repeated_collection_download_records_one_row(
    client, settings, download_collection, downloader, django_capture_on_commit_callbacks
):
    # Repeated downloads within the sentinel window record a single CollectionDownload row
    settings.MAX_DOWNLOADS_PER_DAY = 200
    url = reverse("download-collection", args=[download_collection.id, slugify(download_collection.name)])
    with mock.patch("fscollections.views.download_sounds", return_value=HttpResponse()):
        for _ in range(3):
            with django_capture_on_commit_callbacks(execute=True):
                client.get(url)
    assert CollectionDownload.objects.filter(user=downloader).count() == 1


def test_bookmark_category_download_over_limit_returns_429_and_does_not_increment_download_count(
    client, settings, bookmark_category, downloader
):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    increment_daily_download_count(downloader.id)
    response = client.get(reverse("download-bookmark-category", args=[bookmark_category.id]))
    assert response.status_code == 429
    # Bookmark-category downloads do not have a download-row model, so assert the
    # failed over-limit request did not advance the count.
    assert get_daily_download_count(downloader.id) == 1


def test_sound_page_hides_download_href_when_over_limit(
    client, settings, download_sound, downloader, sound_download_url, moderators_group
):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    url = reverse("sound", args=[download_sound.user.username, download_sound.id])

    response = client.get(url)
    assert not response.context["download_limit_reached"]
    assertContains(response, 'href="%s' % sound_download_url)

    increment_daily_download_count(downloader.id)
    response = client.get(url)
    assert response.context["download_limit_reached"]
    assertNotContains(response, 'href="%s' % sound_download_url)
    assertContains(response, "download-limit-modal")


def test_pack_page_hides_download_href_when_over_limit(client, settings, download_pack, downloader, moderators_group):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    url = reverse("pack", args=[download_pack.user.username, download_pack.id])
    download_path = reverse("pack-download", args=[download_pack.user.username, download_pack.id])

    response = client.get(url)
    assert not response.context["download_limit_reached"]
    assertContains(response, 'href="%s' % download_path)

    increment_daily_download_count(downloader.id)
    response = client.get(url)
    assert response.context["download_limit_reached"]
    assertNotContains(response, 'href="%s' % download_path)
    assertContains(response, "download-limit-modal")


def test_collection_page_hides_download_href_when_over_limit(client, settings, public_collection, downloader):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    url = reverse("collection", args=[public_collection.id, slugify(public_collection.name)])

    response = client.get(url)
    assert not response.context["download_limit_reached"]
    assertContains(response, 'href="%s' % public_collection.download_url)

    increment_daily_download_count(downloader.id)
    response = client.get(url)
    assert response.context["download_limit_reached"]
    assertNotContains(response, 'href="%s' % public_collection.download_url)
    assertContains(response, "download-limit-modal")


def test_bookmarks_page_hides_download_href_when_over_limit(client, settings, bookmark_category, downloader):
    settings.MAX_DOWNLOADS_PER_DAY = 1
    download_path = reverse("download-bookmark-category", args=[bookmark_category.id])

    response = client.get(reverse("bookmarks"))
    assert not response.context["download_limit_reached"]
    assertContains(response, 'href="%s' % download_path)

    increment_daily_download_count(downloader.id)
    response = client.get(reverse("bookmarks"))
    assert response.context["download_limit_reached"]
    assertNotContains(response, 'href="%s' % download_path)
    assertContains(response, "download-limit-modal")


def test_modal_view_returns_limit_content(client, downloader):
    response = client.get(reverse("download-limit-modal") + "?ajax=1")
    assert response.status_code == 200
    assert b"download limit" in response.content.lower()
