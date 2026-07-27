from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from utils.ratelimit import RequestLimitReason, count_request_limit_event, request_limit_events_total
from utils.test_helpers import counter_samples


def _samples():
    return counter_samples(request_limit_events_total, "reason", "enforced", "user_type")


def test_count_request_limit_event_labels_anonymous():
    req = RequestFactory().get("/search/")
    req.user = AnonymousUser()
    before = _samples().get(("search_page_limit", "true", "anonymous"), 0)
    count_request_limit_event(req, RequestLimitReason.SEARCH_PAGE_LIMIT, enforced=True)
    assert _samples()[("search_page_limit", "true", "anonymous")] == before + 1


def test_count_request_limit_event_labels_authenticated():
    req = RequestFactory().get("/search/")
    req.user = User(username="u")
    before = _samples().get(("django_ratelimit", "false", "authenticated"), 0)
    count_request_limit_event(req, RequestLimitReason.DJANGO_RATELIMIT, enforced=False)
    assert _samples()[("django_ratelimit", "false", "authenticated")] == before + 1
