"""
Unit tests for client-IP derivation used by the auth rate limiter.

The leftmost X-Forwarded-For entry is client-controlled, so rotating it must not
yield a fresh rate-limit bucket. The real client IP is the entry appended by the
trusted proxy (TRUSTED_PROXY_COUNT hops from the right).
"""

import os

import pytest
from fastapi.testclient import TestClient


def _import_api():
    """Import app.api, which needs OPENAI_API_KEY set at import time.

    The placeholder key is removed again afterwards so it does not un-skip
    other tests that check for a real key.
    """
    if os.environ.get("OPENAI_API_KEY"):
        import app.api as module
        return module
    os.environ["OPENAI_API_KEY"] = "test-placeholder"
    try:
        import app.api as module
    finally:
        os.environ.pop("OPENAI_API_KEY", None)
    return module


api = _import_api()


# Address of the reverse proxy as seen on the socket (Railway's edge uses
# CGNAT-range peers), and two distinct real clients behind it.
PROXY_PEER = ("100.64.0.2", 40000)
CLIENT_A = "203.0.113.7"
CLIENT_B = "198.51.100.23"

LOGIN_LIMIT = api.RATE_LIMITS["login"]["max_requests"]


class _FakeDB:
    """Stands in for the database so login reaches its normal 'not found' path."""

    def get_user_by_email(self, email):
        return None


@pytest.fixture(autouse=True)
def isolated_api(monkeypatch):
    monkeypatch.setattr(api, "rate_limiter", api.RateLimiter())
    monkeypatch.setattr(api, "TRUSTED_PROXY_COUNT", 1)
    monkeypatch.setattr(api, "check_db", lambda: _FakeDB())


@pytest.fixture
def client():
    # Not used as a context manager, so the app lifespan (DB warm-up etc.) does not run.
    return TestClient(api.app, client=PROXY_PEER)


def _login(client, xff=None, headers=None):
    if headers is None:
        headers = {"X-Forwarded-For": xff} if xff is not None else {}
    return client.post(
        "/auth/login",
        json={"email": "someone@example.com", "password": "wrong-password"},
        headers=headers,
    )


@pytest.mark.unit
class TestSpoofedForwardedFor:
    def test_rotating_spoofed_leftmost_value_does_not_reset_limit(self, client):
        """Attacker varies the leftmost XFF entry; the proxy appends the real IP."""
        for i in range(LOGIN_LIMIT):
            resp = _login(client, f"10.9.{i}.{i}, {CLIENT_A}")
            assert resp.status_code == 200, resp.text

        resp = _login(client, f"10.9.99.99, {CLIENT_A}")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_rotating_multiple_spoofed_entries_does_not_reset_limit(self, client):
        for i in range(LOGIN_LIMIT):
            resp = _login(client, f"1.1.1.{i}, 2.2.2.{i}, 3.3.3.{i}, {CLIENT_A}")
            assert resp.status_code == 200, resp.text

        assert _login(client, f"9.9.9.9, 8.8.8.8, {CLIENT_A}").status_code == 429

    def test_separate_spoofed_header_line_is_not_trusted(self, client):
        """Client sends its own XFF line; the proxy adds another line after it."""
        for i in range(LOGIN_LIMIT):
            headers = [("X-Forwarded-For", f"10.0.0.{i}"), ("X-Forwarded-For", CLIENT_A)]
            assert _login(client, headers=headers).status_code == 200

        headers = [("X-Forwarded-For", "10.0.0.250"), ("X-Forwarded-For", CLIENT_A)]
        assert _login(client, headers=headers).status_code == 429


@pytest.mark.unit
class TestRealClientIp:
    def test_proxy_appended_ip_is_the_rate_limit_key(self, client):
        for _ in range(LOGIN_LIMIT):
            assert _login(client, f"spoofed, {CLIENT_A}").status_code == 200
        assert _login(client, CLIENT_A).status_code == 429

        # A different real client behind the same proxy has its own bucket.
        assert _login(client, f"spoofed, {CLIENT_B}").status_code == 200
        assert _login(client, CLIENT_B).status_code == 200

        assert api.rate_limiter._requests[f"login:{CLIENT_A}"]
        assert len(api.rate_limiter._requests[f"login:{CLIENT_B}"]) == 2
        assert not any("spoofed" in key for key in api.rate_limiter._requests)

    def test_missing_header_falls_back_to_socket_peer(self, client):
        for _ in range(LOGIN_LIMIT):
            assert _login(client).status_code == 200
        assert _login(client).status_code == 429
        assert f"login:{PROXY_PEER[0]}" in api.rate_limiter._requests


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    """Minimal Request stand-in for get_client_ip."""

    def __init__(self, xff_values=(), peer="100.64.0.2"):
        from starlette.datastructures import Headers

        raw = [(b"x-forwarded-for", v.encode("latin-1")) for v in xff_values]
        self.headers = Headers(raw=raw)
        self.client = _FakeClient(peer) if peer else None


@pytest.mark.unit
class TestGetClientIp:
    @pytest.mark.parametrize(
        "count, xff, expected",
        [
            (1, ["203.0.113.7"], "203.0.113.7"),
            (1, ["evil, 203.0.113.7"], "203.0.113.7"),
            (1, ["evil", "203.0.113.7"], "203.0.113.7"),
            (1, [" evil ,, 203.0.113.7 "], "203.0.113.7"),
            (2, ["evil, 203.0.113.7, 10.0.0.5"], "203.0.113.7"),
            (2, ["203.0.113.7, 10.0.0.5"], "203.0.113.7"),
            # Fewer entries than trusted proxies: don't trust the header.
            (2, ["203.0.113.7"], "100.64.0.2"),
            # Header absent or empty.
            (1, [], "100.64.0.2"),
            (1, [""], "100.64.0.2"),
            (1, [" , "], "100.64.0.2"),
            # Count 0: app is exposed directly, header is ignored.
            (0, ["evil, 203.0.113.7"], "100.64.0.2"),
        ],
    )
    def test_selects_entry_counted_from_right(self, monkeypatch, count, xff, expected):
        monkeypatch.setattr(api, "TRUSTED_PROXY_COUNT", count)
        assert api.get_client_ip(_FakeRequest(xff)) == expected

    def test_no_socket_peer(self, monkeypatch):
        monkeypatch.setattr(api, "TRUSTED_PROXY_COUNT", 1)
        assert api.get_client_ip(_FakeRequest([], peer=None)) == "unknown"


@pytest.mark.unit
class TestParseTrustedProxyCount:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            (None, 1),
            ("", 1),
            ("  ", 1),
            ("0", 0),
            ("1", 1),
            (" 2 ", 2),
            ("abc", 1),
            ("-1", 1),
            ("1.5", 1),
        ],
    )
    def test_parse(self, raw, expected):
        assert api._parse_trusted_proxy_count(raw) == expected
