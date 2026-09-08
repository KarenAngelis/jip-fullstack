from datetime import timedelta

import pytest
from jose import jwt
from app.models.user_model import User
from app.models.account_settings_model import AccountSettings
from app.services.auth_service import (
    AuthService, SECRET_KEY, ALGORITHM, ISSUER, AUDIENCE,
)


def claims(account):
    return jwt.decode(account["token"], SECRET_KEY, algorithms=[ALGORITHM],
                      audience=AUDIENCE, issuer=ISSUER)


def test_registration_login_and_private_responses(client, db, accounts, auth_headers):
    alice, _ = accounts
    stored = db.get(User, alice["id"])
    assert stored.hashed_password != alice["credentials"]["password"]
    assert AuthService.verify_password(alice["credentials"]["password"], stored.hashed_password)
    for route in ("/api/auth/me", "/api/auth/verify-token"):
        response = client.get(route, headers=auth_headers(alice))
        assert response.status_code == 200
        assert "hashed_password" not in response.text
        assert alice["credentials"]["password"] not in response.text
        user = response.json().get("user", response.json())
        assert user["id"] == alice["id"]
    decoded = claims(alice)
    assert decoded["exp"] - decoded["iat"] == 30 * 60


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer invalid", "Bearer"])
def test_missing_or_malformed_token_is_unauthorized(client, authorization):
    headers = {"Authorization": authorization} if authorization else {}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("case", ["expired", "missing_exp", "wrong_signature", "wrong_issuer",
                                  "wrong_audience", "missing_sub", "wrong_algorithm"])
def test_untrusted_jwt_is_rejected(client, accounts, case):
    alice, _ = accounts
    payload = claims(alice)
    key, algorithm = SECRET_KEY, ALGORITHM
    if case == "expired":
        token = AuthService.create_access_token({"sub": alice["email"]}, timedelta(seconds=-60))
    else:
        if case == "missing_exp":
            payload.pop("exp")
        elif case == "wrong_signature":
            key = "different-test-signing-key-00000000000"
        elif case == "wrong_issuer":
            payload["iss"] = "another-service"
        elif case == "wrong_audience":
            payload["aud"] = "another-client"
        elif case == "missing_sub":
            payload.pop("sub")
        elif case == "wrong_algorithm":
            algorithm = "HS384"
        token = jwt.encode(payload, key, algorithm=algorithm)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_explicit_lifetime_is_honored(accounts):
    token = AuthService.create_access_token({"sub": accounts[0]["email"]}, timedelta(minutes=5))
    payload = claims({"token": token})
    assert payload["exp"] - payload["iat"] == 300


def test_wrong_password_cannot_login(client, accounts):
    response = client.post("/api/auth/login", json={
        "email": accounts[0]["email"], "password": "wrong-password"})
    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_deleted_user_token_is_rejected(client, db, accounts, auth_headers):
    alice, _ = accounts
    db.delete(db.get(User, alice["id"]))
    db.commit()
    assert client.get("/api/auth/me", headers=auth_headers(alice)).status_code == 401


def test_inactive_user_cannot_login_or_use_old_token(client, db, accounts, auth_headers):
    alice, _ = accounts
    db.get(User, alice["id"]).is_active = False
    db.commit()
    assert client.post("/api/auth/login", json=alice["credentials"]).status_code == 401
    assert client.get("/api/auth/me", headers=auth_headers(alice)).status_code == 400
    assert client.get("/settings/me", headers=auth_headers(alice)).status_code == 400


def test_settings_reads_and_updates_are_scoped_to_token(client, db, accounts, auth_headers):
    alice, bob = accounts
    for account in accounts:
        response = client.put("/settings/me", headers=auth_headers(account), json={
            "display_name": account["nome"], "bio": f"Private bio of {account['nome']}"})
        assert response.status_code == 200
        assert response.json()["user_id"] == account["id"]
    response = client.get(f"/settings/me?user_id={bob['id']}", headers=auth_headers(alice))
    assert response.json()["user_id"] == alice["id"]
    assert "Private bio of bob" not in response.text
    response = client.patch("/settings/me", headers=auth_headers(alice), json={"bio": "Updated Alice"})
    assert response.status_code == 200
    assert db.query(AccountSettings).filter_by(user_id=bob["id"]).one().bio == "Private bio of bob"
    assert client.get("/settings/me", headers=auth_headers(bob)).json()["bio"] == "Private bio of bob"


@pytest.mark.parametrize("method", ["put", "patch"])
def test_cannot_select_another_settings_owner(client, db, accounts, auth_headers, method):
    alice, bob = accounts
    client.put("/settings/me", headers=auth_headers(bob), json={"display_name": "Bob original"})
    response = getattr(client, method)("/settings/me", headers=auth_headers(alice), json={
        "user_id": bob["id"], "display_name": "Tampered profile"})
    assert response.status_code == 422
    assert db.query(AccountSettings).filter_by(user_id=bob["id"]).one().display_name == "Bob original"
    assert db.query(AccountSettings).filter_by(user_id=alice["id"]).first() is None


@pytest.mark.parametrize("method", ["get", "put", "patch"])
def test_settings_require_authentication(client, method):
    kwargs = {} if method == "get" else {"json": {"display_name": "Anonymous"}}
    response = getattr(client, method)("/settings/me", **kwargs)
    assert response.status_code == 401


def test_invalid_settings_are_client_error(client, accounts, auth_headers):
    response = client.put("/settings/me", headers=auth_headers(accounts[0]), json={"display_name": ""})
    assert response.status_code == 422


@pytest.mark.parametrize("variable,value", [
    ("SECRET_KEY", ""), ("SECRET_KEY", "short"),
    ("ACCESS_TOKEN_EXPIRE_MINUTES", "0"), ("ACCESS_TOKEN_EXPIRE_MINUTES", "-1"),
])
def test_unsafe_auth_configuration_fails_at_startup(variable, value):
    import os
    import subprocess
    import sys

    environment = {**os.environ, variable: value}
    result = subprocess.run(
        [sys.executable, "-c", "from app.services.auth_service import AuthService"],
        env=environment, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0
    assert f"RuntimeError: {variable}" in result.stderr
