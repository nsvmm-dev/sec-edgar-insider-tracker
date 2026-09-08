"""Thin, rate-limited HTTP client for SEC EDGAR.

SEC requires a descriptive User-Agent and asks for <= 10 requests/second. This
client enforces a minimum delay between requests and retries transient errors.
SEC provides no technical support, so callers must handle parse failures.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .config import settings

_RETRY_STATUS = {403, 429, 500, 502, 503, 504}


class SecClient:
    def __init__(
        self,
        user_agent: str | None = None,
        delay_sec: float | None = None,
        max_retries: int = 4,
    ) -> None:
        self.user_agent = user_agent or settings.sec_user_agent
        self.delay_sec = settings.sec_request_delay_sec if delay_sec is None else delay_sec
        self.max_retries = max_retries
        self._last_request_ts = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)

    def _request(self, url: str) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                resp = self._session.get(url, timeout=30)
                self._last_request_ts = time.monotonic()
            except requests.RequestException as exc:  # network-level failure
                last_exc = exc
                time.sleep(min(2**attempt, 10))
                continue

            if resp.status_code == 200:
                return resp
            if resp.status_code == 404:
                resp.raise_for_status()  # not retryable — surface immediately
            if resp.status_code in _RETRY_STATUS:
                last_exc = requests.HTTPError(f"{resp.status_code} for {url}")
                time.sleep(min(2**attempt, 10))
                continue
            resp.raise_for_status()

        raise RuntimeError(
            f"SEC request failed after {self.max_retries} attempts: {url}"
        ) from last_exc

    def get_text(self, url: str) -> str:
        return self._request(url).text

    def get_json(self, url: str) -> Any:
        return self._request(url).json()
