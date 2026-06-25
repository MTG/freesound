import hmac
import logging
import os

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    generate_latest,
    push_to_gateway,
)
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.multiprocess import MultiProcessCollector

logger = logging.getLogger("commands")


def _authorized(request):
    expected = getattr(settings, "PROMETHEUS_METRICS_TOKEN", None)
    header = request.META.get("HTTP_AUTHORIZATION", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    return hmac.compare_digest(header[len(prefix) :], expected)


@require_GET
def prometheus_metrics_view(request):
    """GET view that returns prometheus metrics for this webserver.
    Because gunicorn runs multiple subprocesses, we use the built-in
    PROMETHEUS_MULTIPROC_DIR functionality in prometheus_client: If it's set
    to a directory then different processes automatically write metrics there and
    whatever process gets the request will aggregate and return them.
    When running as a single process (dev server) then just return in-memory metrics."""
    if not getattr(settings, "PROMETHEUS_METRICS_TOKEN", None):
        return HttpResponse(status=404)
    if not _authorized(request):
        return HttpResponse("Unauthorized", status=401)
    if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
        output = generate_latest(registry)
    else:
        output = generate_latest()
    return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)


def push_to_gateway_safe(job, registry):
    url: str | None = getattr(settings, "PROMETHEUS_PUSHGATEWAY_URL", None)
    if not url:
        return
    timeout = getattr(settings, "PROMETHEUS_PUSHGATEWAY_TIMEOUT_SECONDS", 5)
    try:
        push_to_gateway(url, job=job, registry=registry, timeout=timeout)
    except Exception:
        logger.warning("Failed to push metrics to Pushgateway", exc_info=True)


class ManagementCommandCollector:
    """Stats to store for a management command. We store one metric per command marking
    how long the last run took and what its status was. Details of the command are sent
    to the pushgateway."""

    def __init__(self, duration_seconds, success):
        self.duration_seconds = duration_seconds
        self.success = success

    def collect(self):
        duration = GaugeMetricFamily(
            "freesound_management_command_last_duration_seconds",
            "Duration of last command run",
        )
        duration.add_metric([], self.duration_seconds)
        yield duration

        success = GaugeMetricFamily(
            "freesound_management_command_last_success",
            "Whether last command run succeeded (1=ok, 0=error)",
        )
        success.add_metric([], 1 if self.success else 0)
        yield success


def make_command_registry(duration_seconds, success):
    registry = CollectorRegistry()
    registry.register(ManagementCommandCollector(duration_seconds, success))
    return registry
