"""Search aggregates. Query text, URLs, users and IPs belong in the archive/logs."""

from typing import Literal

from prometheus_client import Counter, Histogram

from utils.prometheus_metrics import SERVICE_DURATION_BUCKETS_SECONDS

_searches = Counter(
    "freesound_search_requests_total", "Successful or timed-out searches", ["source", "kind", "outcome"]
)
_query_time = Histogram(
    "freesound_search_query_duration_seconds",
    "Solr QTime for successful searches (excludes cache hits; not HTTP response time)",
    ["source", "kind"],
    buckets=SERVICE_DURATION_BUCKETS_SECONDS,
)
slow_queries = Counter("freesound_solr_slow_queries_total", "Solr responses exceeding the configured slow threshold")
partial_results = Counter("freesound_solr_partial_results_total", "Solr responses rejected because timeAllowed expired")
random_queries = Counter("freesound_solr_random_sound_queries_total", "Random-sound selection attempts")


def record_search(
    source: Literal["web", "tags", "api", "forum", "tag_cloud"],
    *,
    similar_to: int | list[float] | None = None,
    query_time_ms: float | None = None,
    outcome: Literal["success", "timeout"] = "success",
) -> None:
    """Count a search outcome by caller and text/similarity kind.

    Observe successful Solr QTime in seconds when a non-negative timing is
    available. Cached results with no timing still increment the search count.
    """
    kind = "similarity" if similar_to else "text"
    _searches.labels(source, kind, outcome).inc()
    if outcome == "success" and query_time_ms is not None and query_time_ms >= 0:
        _query_time.labels(source, kind).observe(query_time_ms / 1000)
