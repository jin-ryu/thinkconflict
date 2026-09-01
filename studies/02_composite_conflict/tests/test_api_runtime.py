from pathlib import Path

import httpx
import pytest
from openai import APIStatusError, APITimeoutError

import composite_conflict.api_runtime as api_runtime
from composite_conflict.api_runtime import (
    RequestThrottle,
    completion_with_retry,
    resolve_api_key,
)


def test_resolve_api_key_uses_env_before_dotenv(monkeypatch, tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_API_KEY=file-value\n")
    monkeypatch.setenv("TEST_API_KEY", "env-value")
    assert resolve_api_key(env_name="TEST_API_KEY", env_file=env_file) == "env-value"


def test_resolve_api_key_reads_dotenv(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# secret\nTEST_API_KEY='file-value'\n")
    assert resolve_api_key(env_name="TEST_API_KEY", env_file=env_file) == "file-value"


def test_resolve_api_key_rejects_missing(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("TEST_API_KEY", raising=False)
    with pytest.raises(ValueError, match="missing API key"):
        resolve_api_key(env_name="TEST_API_KEY", env_file=tmp_path / "missing")


def test_completion_without_retry_calls_once():
    calls = []

    class Completions:
        def create(self, **request):
            calls.append(request)
            return "ok"

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    result = completion_with_retry(
        client=Client(),
        request={"model": "test"},
        throttle=RequestThrottle(0),
        max_retries=0,
        retry_base_delay_seconds=60,
    )
    assert result == "ok"
    assert calls == [{"model": "test"}]


def test_throttle_waits_from_completion_before_next_start():
    now = [0.0]
    events = []

    def clock():
        return now[0]

    def sleep(seconds):
        events.append(("sleep", seconds))
        now[0] += seconds

    class Completions:
        def create(self, **request):
            events.append(("start", now[0]))
            now[0] += 7.0
            events.append(("complete", now[0]))
            return "ok"

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    throttle = RequestThrottle(30.0, clock=clock, sleeper=sleep)
    for _ in range(2):
        completion_with_retry(
            client=Client(),
            request={"model": "test"},
            throttle=throttle,
            max_retries=0,
            retry_base_delay_seconds=60,
        )

    assert events == [
        ("start", 0.0),
        ("complete", 7.0),
        ("sleep", 30.0),
        ("start", 37.0),
        ("complete", 44.0),
    ]


def test_throttle_waits_after_failed_request():
    now = [0.0]
    events = []
    should_fail = [True, False]

    def clock():
        return now[0]

    def sleep(seconds):
        events.append(("sleep", seconds))
        now[0] += seconds

    class Completions:
        def create(self, **request):
            events.append(("start", now[0]))
            now[0] += 5.0
            if should_fail.pop(0):
                events.append(("failed", now[0]))
                raise RuntimeError("test failure")
            events.append(("complete", now[0]))
            return "ok"

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    throttle = RequestThrottle(30.0, clock=clock, sleeper=sleep)
    with pytest.raises(RuntimeError, match="test failure"):
        completion_with_retry(
            client=Client(),
            request={"model": "test"},
            throttle=throttle,
            max_retries=0,
            retry_base_delay_seconds=60,
        )
    completion_with_retry(
        client=Client(),
        request={"model": "test"},
        throttle=throttle,
        max_retries=0,
        retry_base_delay_seconds=60,
    )

    assert events == [
        ("start", 0.0),
        ("failed", 5.0),
        ("sleep", 30.0),
        ("start", 35.0),
        ("complete", 40.0),
    ]


def test_503_uses_configured_backoff(monkeypatch):
    calls = []
    sleeps = []

    class Completions:
        def create(self, **request):
            calls.append(request)
            if len(calls) == 1:
                response = httpx.Response(
                    503,
                    request=httpx.Request("POST", "https://example.test"),
                )
                raise APIStatusError("busy", response=response, body={})
            return "ok"

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    monkeypatch.setattr(api_runtime.time, "sleep", sleeps.append)
    result = completion_with_retry(
        client=Client(),
        request={"model": "test"},
        throttle=RequestThrottle(0),
        max_retries=1,
        retry_base_delay_seconds=30,
        retry_delays_seconds=(300,),
        retry_status_codes={503},
        retry_timeouts=False,
        retry_connection_errors=False,
    )
    assert result == "ok"
    assert len(calls) == 2
    assert sleeps == [300]


def test_timeout_is_not_retried_in_503_only_mode(monkeypatch):
    calls = []
    sleeps = []

    class Completions:
        def create(self, **request):
            calls.append(request)
            raise APITimeoutError(request=httpx.Request("POST", "https://example.test"))

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    monkeypatch.setattr(api_runtime.time, "sleep", sleeps.append)
    with pytest.raises(APITimeoutError):
        completion_with_retry(
            client=Client(),
            request={"model": "test"},
            throttle=RequestThrottle(0),
            max_retries=2,
            retry_base_delay_seconds=30,
            retry_delays_seconds=(300, 900),
            retry_status_codes={503},
            retry_timeouts=False,
            retry_connection_errors=False,
        )
    assert len(calls) == 1
    assert sleeps == []
