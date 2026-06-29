from app.services.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# --- unit: hashing & tokens -------------------------------------------------

def test_password_hash_roundtrips():
    hashed = hash_password("hunter2hunter2")
    assert hashed != "hunter2hunter2"  # never store plaintext
    assert verify_password("hunter2hunter2", hashed)
    assert not verify_password("wrong-password", hashed)


def test_token_roundtrips():
    token = create_access_token(subject="42")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_tampered_token_is_rejected():
    token = create_access_token(subject="42")
    assert decode_access_token(token + "x") is None


def test_expired_token_is_rejected():
    token = create_access_token(subject="42", expires_in=-1)
    assert decode_access_token(token) is None


# --- endpoint flow ----------------------------------------------------------

def test_signup_returns_token(client):
    res = client.post("/auth/signup", json={"email": "a@b.com", "password": "password123"})
    assert res.status_code == 201
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_signup_rejects_duplicate_email(client):
    client.post("/auth/signup", json={"email": "dup@b.com", "password": "password123"})
    res = client.post("/auth/signup", json={"email": "dup@b.com", "password": "password123"})
    assert res.status_code == 400


def test_login_succeeds_with_correct_password(client):
    client.post("/auth/signup", json={"email": "log@b.com", "password": "password123"})
    res = client.post("/auth/login", json={"email": "log@b.com", "password": "password123"})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_login_fails_with_wrong_password(client):
    client.post("/auth/signup", json={"email": "wp@b.com", "password": "password123"})
    res = client.post("/auth/login", json={"email": "wp@b.com", "password": "nope-nope-nope"})
    assert res.status_code == 401


def test_login_fails_for_unknown_user(client):
    res = client.post("/auth/login", json={"email": "ghost@b.com", "password": "password123"})
    assert res.status_code == 401


def test_me_returns_current_user_with_token(client):
    signup = client.post("/auth/signup", json={"email": "me@b.com", "password": "password123"})
    token = signup.json()["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@b.com"
    assert "hashed_password" not in res.json()  # never leak the hash


def test_me_requires_authentication(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_garbage_token(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401
