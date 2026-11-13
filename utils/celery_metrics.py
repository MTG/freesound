from threading import Thread
from wsgiref.simple_server import make_server

from celery import bootsteps
from django.conf import settings
from prometheus_client import CollectorRegistry, make_wsgi_app
from prometheus_client.exposition import ThreadingWSGIServer
from prometheus_client.multiprocess import MultiProcessCollector

from utils.prometheus_metrics import metrics_authorized


def authenticated_metrics_app(registry):
    """A prometheus make_wsgi_app app which also checks for an Authorization header like
    our django /metrics endpoint.
    """
    metrics_app = make_wsgi_app(registry)

    def application(environ, start_response):
        if not metrics_authorized(environ.get("HTTP_AUTHORIZATION", "")):
            start_response("401 Unauthorized", [("Content-Type", "text/plain")])
            return [b"Unauthorized"]
        return metrics_app(environ, start_response)

    return application


class WorkerMetrics(bootsteps.StartStopStep):
    requires = ("celery.worker.components:Pool",)

    def __init__(self, worker, **kwargs):
        self.server = None
        self.thread = None

    def include_if(self, worker):
        return bool(settings.PROMETHEUS_METRICS_TOKEN)

    def start(self, worker):
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
        self.server = make_server(
            "0.0.0.0",  # noqa: S104
            9100,
            authenticated_metrics_app(registry),
            server_class=ThreadingWSGIServer,
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self, worker):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.server = None
            self.thread = None

    terminate = stop
