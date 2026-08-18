from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; PersonalCardPriceMonitor/0.1; "
    "+local-personal-use)"
)


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "ja,en;q=0.8"})
    return session


@dataclass
class PoliteRequester:
    """Small rate limiter shared by a collector's sequential requests."""

    session: requests.Session
    delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    _last_request_at: float = field(default=0.0, init=False)

    def get(self, url: str, **kwargs: object) -> requests.Response:
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at and elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        response = self.session.get(url, timeout=self.timeout_seconds, **kwargs)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response

