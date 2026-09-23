"""Polite, retrying, disk-cached HTTP fetcher.

Every response body is written to ``data/raw/http/<host>/<sha1>`` on first
fetch, so reruns never re-hit SEC or issuer sites. SEC asks for a descriptive
User-Agent and <= 10 requests/second; we stay well under that.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from common.paths import RAW

USER_AGENT = os.environ.get("SEC_USER_AGENT", "levetf-research joshswartz@gmail.com")
CACHE_DIR = RAW / "http"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
_lock = threading.Lock()
_last_call: dict[str, float] = {}
MIN_INTERVAL = {"www.sec.gov": 0.15, "efts.sec.gov": 0.15, "data.sec.gov": 0.15}


class FetchError(RuntimeError):
    pass


def _cache_path(url: str) -> Path:
    host = urlparse(url).netloc or "local"
    return CACHE_DIR / host / hashlib.sha1(url.encode()).hexdigest()


def _throttle(host: str) -> None:
    gap = MIN_INTERVAL.get(host, 0.3)
    with _lock:
        wait = _last_call.get(host, 0.0) + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()


def fetch(url: str, *, refresh: bool = False, retries: int = 5, timeout: float = 60.0,
          allow_404: bool = False) -> bytes | None:
    """Return the body of ``url``, from disk cache when available.

    404s are cached as empty markers when ``allow_404`` so they are not retried.
    """
    path = _cache_path(url)
    miss = path.with_suffix(".404")
    if not refresh:
        if path.exists():
            return path.read_bytes()
        if allow_404 and miss.exists():
            return None
    host = urlparse(url).netloc
    delay = 2.0
    for attempt in range(retries):
        _throttle(host)
        try:
            r = _session.get(url, timeout=timeout)
        except requests.RequestException as e:  # network error: back off and retry
            err = e
        else:
            if r.status_code == 200:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(r.content)
                tmp.replace(path)
                return r.content
            if r.status_code == 404 and allow_404:
                path.parent.mkdir(parents=True, exist_ok=True)
                miss.write_bytes(b"")
                return None
            err = FetchError(f"HTTP {r.status_code} for {url}")
            if r.status_code in (403, 404) and attempt >= 1:
                break
        time.sleep(delay)
        delay *= 2
    raise FetchError(f"failed after {retries} attempts: {url}: {err}")
