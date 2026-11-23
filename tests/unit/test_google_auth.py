"""
Tests for POST /auth/google (Sign in with Google).

The endpoint must only issue a session for a Google ID token that verifies
server-side. Tokens here are real RS256 JWTs signed with a throwaway key;
google-auth's own verification runs unmodified, and only the HTTP transport it
uses to download Google's signing certificates is replaced with a stub that
serves the test certificate. No network access or database is needed.

Like tests/test_api.py, importing app.api requires OPENAI_API_KEY to be set
(any value works).
"""

import datetime as dt
import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from app import api


CLIENT_ID = "test-client-id.apps.googleusercontent.com"
KEY_ID = "test-key-id"


# ============================================================================
# Helpers
# ============================================================================

def _new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _self_signed_cert_pem(key) -> str:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-google-signer")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


SIGNING_KEY = _new_rsa_key()
SIGNING_CERT_PEM = _self_signed_cert_pem(SIGNING_KEY)


def make_id_token(key=SIGNING_KEY, kid=KEY_ID, algorithm="RS256", **overrides) -> str:
    """Build a Google-style ID token. Pass a claim as None to omit it."""
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "azp": CLIENT_ID,
        "aud": CLIENT_ID,
        "sub": "109876543210987654321",
        "email": "alice@example.com",
        "email_verified": True,
        "name": "Alice Example",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


class FakeCertsTransport:
    """Stands in for google.auth.transport.requests.Request.

    Serves the test signing certificate at Google's cert endpoint.
    """

    def __init__(self, status=200):
        self.status = status
        self.urls = []

    def __call__(self, url, method="GET", **kwargs):
        self.urls.append(url)
        body = json.dumps({KEY_ID: SIGNING_CERT_PEM}).encode()
        return SimpleNamespace(status=self.status, data=body, headers={})


class FakeDB:
    def __init__(self, users=None):
        self.users = {u["email"]: dict(u) for u in (users or [])}
        self.created = []
        self.updated = []
        self.lookups = []

    def get_user_by_email(self, email):
        self.lookups.append(email)
        user = self.users.get(email)
        return dict(user) if user else None

    def update_user_profile(self, user_id, **fields):
        self.updated.append((user_id, fields))
        return True

    def create_user(self, email, password_hash=None, name=None):
        user = {"id": 1000 + len(self.created), "email": email, "name": name,
                "password_hash": password_hash}
        self.created.append(user)
        self.users[email] = user
        return dict(user)


ALICE = {"id": 7, "email": "alice@example.com", "name": "Alice Example",
         "password_hash": None, "age": 30, "weight": 60}
VICTIM = {"id": 42, "email": "victim@example.com", "name": "Victim",
          "password_hash": "x", "age": 40, "weight": 80}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db():
    return FakeDB(users=[ALICE, VICTIM])


@pytest.fixture
def transport():
    return FakeCertsTransport()


@pytest.fixture
def client(monkeypatch, db, transport):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-for-google-auth-tests")
    monkeypatch.setattr(api, "check_db", lambda: db)
    monkeypatch.setattr(api, "_google_transport_request", lambda: transport)
    # Fresh limiter so the rate-limit state doesn't leak between tests
    monkeypatch.setattr(api, "rate_limiter", api.RateLimiter())
    return TestClient(api.app)


def post_google(client, body):
    return client.post("/auth/google", json=body)


def assert_rejected(response, db, status=401):
    assert response.status_code == status, response.text
    body = response.json()
    assert "token" not in body or body.get("token") is None
    assert body.get("success") is not True
    # Rejection must happen before any account is looked up or created
    assert db.lookups == []
    assert db.created == []


# ============================================================================
# Successful sign-in
# ============================================================================

class TestValidToken:

    def test_valid_token_logs_in_existing_user(self, client, db, transport):
        r = post_google(client, {"credential": make_id_token()})

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["user"]["id"] == ALICE["id"]
        assert body["user"]["email"] == "alice@example.com"
        assert api.decode_access_token(body["token"]) == ALICE["id"]
        assert db.created == []
        # Signing certs were fetched from Google's endpoint
        assert transport.urls == ["https://www.googleapis.com/oauth2/v1/certs"]

    def test_valid_token_creates_new_user_from_claims(self, client, db):
        token = make_id_token(email="New.User@Example.com", name="New User")
        r = post_google(client, {"credential": token})

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert db.created == [{"id": 1000, "email": "new.user@example.com",
                               "name": "New User", "password_hash": None}]
        assert api.decode_access_token(body["token"]) == 1000

    def test_name_is_taken_from_token_claims(self, client, db):
        r = post_google(client, {"credential": make_id_token(name="Alice Renamed")})

        assert r.status_code == 200
        assert r.json()["user"]["name"] == "Alice Renamed"
        assert db.updated == [(ALICE["id"], {"name": "Alice Renamed"})]

    def test_client_supplied_email_and_name_are_ignored(self, client, db):
        """Extra fields in the body must not override the verified identity."""
        r = post_google(client, {
            "credential": make_id_token(),  # Alice's token
            "email": VICTIM["email"],
            "name": "Mallory",
        })

        assert r.status_code == 200
        body = r.json()
        assert body["user"]["id"] == ALICE["id"]
        assert body["user"]["email"] == ALICE["email"]
        assert api.decode_access_token(body["token"]) == ALICE["id"]
        assert db.lookups == [ALICE["email"]]

    def test_issuer_without_scheme_is_accepted(self, client):
        r = post_google(client, {"credential": make_id_token(iss="accounts.google.com")})
        assert r.status_code == 200
        assert r.json()["success"] is True


# ============================================================================
# Account-takeover regression: no credential, no session
# ============================================================================

class TestMissingCredential:

    def test_bare_email_is_rejected(self, client, db):
        r = post_google(client, {"email": VICTIM["email"], "name": "Victim"})
        assert_rejected(r, db)

    def test_bare_email_with_picture_is_rejected(self, client, db):
        r = post_google(client, {"email": VICTIM["email"], "name": "V",
                                 "picture": "https://example.com/p.png"})
        assert_rejected(r, db)

    def test_empty_body_is_rejected(self, client, db):
        assert_rejected(post_google(client, {}), db)

    @pytest.mark.parametrize("credential", ["", "   ", None])
    def test_blank_credential_is_rejected(self, client, db, credential):
        assert_rejected(post_google(client, {"credential": credential}), db)


# ============================================================================
# Invalid tokens
# ============================================================================

class TestInvalidToken:

    def test_wrong_audience_is_rejected(self, client, db):
        token = make_id_token(aud="someone-elses-app.apps.googleusercontent.com")
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_unverified_email_is_rejected(self, client, db):
        token = make_id_token(email_verified=False)
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_missing_email_verified_claim_is_rejected(self, client, db):
        token = make_id_token(email_verified=None)
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_missing_email_claim_is_rejected(self, client, db):
        token = make_id_token(email=None)
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_expired_token_is_rejected(self, client, db):
        now = int(time.time())
        token = make_id_token(iat=now - 7200, exp=now - 3600)
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_wrong_issuer_is_rejected(self, client, db):
        token = make_id_token(iss="https://evil.example.com")
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_token_signed_by_other_key_is_rejected(self, client, db):
        token = make_id_token(key=_new_rsa_key())
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_unknown_key_id_is_rejected(self, client, db):
        token = make_id_token(kid="not-a-google-key")
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_unsigned_token_is_rejected(self, client, db):
        token = make_id_token(key=None, algorithm="none")
        assert_rejected(post_google(client, {"credential": token}), db)

    def test_hs256_token_is_rejected(self, client, db):
        """Symmetric-key tokens (e.g. our own session JWTs) are not Google ID tokens."""
        token = make_id_token(key="test-secret-for-google-auth-tests", algorithm="HS256")
        assert_rejected(post_google(client, {"credential": token}), db)

    @pytest.mark.parametrize("garbage", ["not-a-jwt", "a.b.c", "x" * 5000])
    def test_malformed_token_is_rejected(self, client, db, garbage):
        assert_rejected(post_google(client, {"credential": garbage}), db)


# ============================================================================
# Configuration, availability and rate limiting
# ============================================================================

class TestConfigurationAndLimits:

    def test_unconfigured_client_id_fails_closed(self, client, db, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        r = post_google(client, {"credential": make_id_token()})
        assert_rejected(r, db, status=503)

    def test_bare_email_rejected_even_when_unconfigured(self, client, db, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        assert_rejected(post_google(client, {"email": VICTIM["email"]}), db)

    def test_cert_fetch_failure_returns_503(self, client, db, transport):
        transport.status = 500
        r = post_google(client, {"credential": make_id_token()})
        assert_rejected(r, db, status=503)

    def test_rate_limited_after_five_attempts(self, client, db):
        for _ in range(5):
            assert post_google(client, {"email": VICTIM["email"]}).status_code == 401

        r = post_google(client, {"credential": make_id_token()})
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert "token" not in r.json()
