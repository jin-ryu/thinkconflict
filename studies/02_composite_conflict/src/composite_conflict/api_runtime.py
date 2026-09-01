"""Safe OpenAI-compatible API credentials, throttling, and retries."""

from __future__ import annotations

import os
import time
from contextlib import nullcontext, contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Iterator, Sequence

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError


def _dotenv_value(path: Path, name: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def resolve_api_key(*, env_name: str | None, env_file: Path | None) -> str:
    if not env_name:
        return "EMPTY"
    value = os.environ.get(env_name)
    if not value and env_file is not None:
        value = _dotenv_value(env_file, env_name)
    if not value:
        location = f" or {env_file}" if env_file is not None else ""
        raise ValueError(f"missing API key in environment variable {env_name}{location}")
    return value


class RequestThrottle:
    """Serialize requests and cool down after each request has completed."""

    def __init__(
        self,
        delay_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if delay_seconds < 0:
            raise ValueError("request delay must be non-negative")
        self.delay_seconds = delay_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._lock = Lock()
        self._last_completed_at: float | None = None

    @contextmanager
    def request_slot(self) -> Iterator[None]:
        """Allow one request at a time, measured completion-to-next-start."""
        with self._lock:
            delay = 0.0
            if self._last_completed_at is not None:
                elapsed = self._clock() - self._last_completed_at
                delay = max(0.0, self.delay_seconds - elapsed)
            if delay:
                self._sleeper(delay)
            try:
                yield
            finally:
                self._last_completed_at = self._clock()


def _server_retry_after(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def create_client(*, base_url: str, api_key: str, timeout_seconds: float) -> OpenAI:
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=0,
    )


def completion_with_retry(
    *,
    client: OpenAI,
    request: dict[str, Any],
    throttle: RequestThrottle | None,
    max_retries: int,
    retry_base_delay_seconds: float,
    retry_delays_seconds: Sequence[float] | None = None,
    retry_status_codes: set[int] | None = None,
    retry_timeouts: bool = True,
    retry_connection_errors: bool = True,
    on_retry: Callable[[int, float, Exception], None] | None = None,
) -> Any:
    if max_retries < 0:
        raise ValueError("max retries must be non-negative")
    if retry_delays_seconds is not None:
        if len(retry_delays_seconds) != max_retries:
            raise ValueError("retry delay count must equal max retries")
        if any(delay < 0 for delay in retry_delays_seconds):
            raise ValueError("retry delays must be non-negative")
    retryable = (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError)
    for attempt in range(max_retries + 1):
        try:
            with (throttle.request_slot() if throttle is not None else nullcontext()):
                return client.chat.completions.create(**request)
        except retryable as error:
            status = getattr(error, "status_code", None)
            if isinstance(error, APITimeoutError) and not retry_timeouts:
                raise
            if isinstance(error, APIConnectionError) and not isinstance(error, APITimeoutError) and not retry_connection_errors:
                raise
            if isinstance(error, APIStatusError) and retry_status_codes is not None and status not in retry_status_codes:
                raise
            if isinstance(error, APIStatusError) and status not in {408, 409, 429} and (status is None or status < 500):
                raise
            if attempt >= max_retries:
                raise
            server_delay = _server_retry_after(error)
            configured_delay = (
                retry_delays_seconds[attempt]
                if retry_delays_seconds is not None
                else retry_base_delay_seconds * (2**attempt)
            )
            delay = max(server_delay or 0.0, configured_delay)
            delay = min(delay, 3600.0)
            if on_retry is not None:
                on_retry(attempt + 1, delay, error)
            time.sleep(delay)
    raise AssertionError("unreachable")
