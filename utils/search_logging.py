import json
import logging
import socket
from collections.abc import Mapping
from datetime import datetime, timezone

from django.conf import settings
from prometheus_client import Counter
from sentry_sdk.integrations.logging import ignore_logger, ignore_logger_for_sentry_logs

ignore_logger("search_archive")
ignore_logger_for_sentry_logs("search_archive")
logger = logging.getLogger("search_archive")
send_events = Counter("freesound_search_archive_send_total", "Archive sender outcomes", ["outcome"])
# Query-parameter allowlists for web/tag searches and API searches, respectively.
WEB_PARAMS = frozenset(
    "q s page f d0 d1 ig r dp g cm mm st cc cid ss w eap se nsm "
    "si_tags si_name si_description si_packname si_collection_names si_sound_id si_username".split()
)
API_PARAMS = frozenset("query page filter weights sort page_size group_by_pack similar_to similarity_space".split())
MAX_DATAGRAM_BYTES = 8192


class SearchArchiveHandler(logging.Handler):
    """Send JSON to a search archiver via UDP. Actions and errors are instrumented with Prometheus."""

    def __init__(self):
        super().__init__()
        self.socket = None
        self.address = (settings.SEARCH_ARCHIVE_HOST, settings.SEARCH_ARCHIVE_PORT)
        if settings.SEARCH_ARCHIVE_ENABLED:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.setblocking(False)
            except Exception:
                self.close()
                send_events.labels("initialization_error").inc()

    def emit(self, record):
        try:
            data = json.dumps(record.msg, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
            if len(data) > MAX_DATAGRAM_BYTES:
                send_events.labels("oversize").inc()
                return
            if self.socket is None:
                send_events.labels("unavailable").inc()
                return
            self.socket.sendto(data, self.address)
            send_events.labels("sent").inc()
        except BlockingIOError:
            send_events.labels("would_block").inc()
        except Exception:
            send_events.labels("error").inc()

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        super().close()


def archive_search(
    *, source: str, params: Mapping[str, str], num_results: int, query_time: float | None, ip: str | None
) -> None:
    """Archive allowlisted search parameters without propagating logging failures."""
    if not settings.SEARCH_ARCHIVE_ENABLED:
        return
    try:
        allowed = API_PARAMS if source == "api" else WEB_PARAMS
        archived_params = {}
        for name, value in params.items():
            if name not in allowed:
                continue
            # Similarity can be supplied as a vector; archive sound IDs only.
            if name in {"st", "similar_to"} and value and not value.isdecimal():
                continue
            if len(value) > 4096:
                send_events.labels("oversize").inc()
                return
            archived_params[name] = value
        logger.info(
            {
                "schema_version": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "params": archived_params,
                "num_results": num_results,
                "query_time_ms": query_time,
                "ip": ip,
            }
        )
    except Exception:
        send_events.labels("construction_error").inc()
