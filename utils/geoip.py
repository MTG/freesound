"""Country lookup from an IP address, using a MaxMind GeoLite2-Country database.

The database is opened on first use and reopened when the file changes (geoipupdate replaces it in place),
so updates take effect without restarting. A missing database or a failed lookup returns an empty string.
"""

import ipaddress
import logging
import os
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_reader = None
_reader_key = None  # (path, mtime) of the open database


def _get_reader():
    global _reader, _reader_key
    path = settings.GEOIP_COUNTRY_DATABASE_PATH
    try:
        key = (path, os.stat(path).st_mtime_ns)
    except (OSError, TypeError):
        return None
    with _lock:
        if key != _reader_key:
            import maxminddb

            try:
                # Load into memory (~3 MB) rather than mmap: on NFS, geoipupdate replacing the file would make
                # reads of a mapped file fail with SIGBUS and kill the worker.
                reader = maxminddb.open_database(path, mode=maxminddb.MODE_MEMORY)
            except Exception:
                logger.warning("GeoIP database at %s could not be opened", path)
                return None
            if _reader is not None:
                _reader.close()
            _reader, _reader_key = reader, key
        return _reader


def get_country_iso_code(ip):
    """Return the 2-letter ISO country code of an IP address, or "" if unknown.

    Accepts the values returned by utils.logging_filters.get_client_ip, including "-" (no IP).
    """
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    reader = _get_reader()
    if reader is None:
        return ""
    try:
        record = reader.get(str(address))
    except Exception:
        logger.warning("GeoIP lookup failed")
        return ""
    code = (record or {}).get("country", {}).get("iso_code")
    if isinstance(code, str) and len(code) == 2 and code.isascii() and code.isalpha() and code.isupper():
        return code
    return ""
