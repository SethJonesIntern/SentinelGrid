# app/services/security.py
#
# Password hashing and bearer-token (JWT) helpers, plus the FastAPI dependency
# that resolves the current user from an Authorization header.
#
# Deliberately dependency-free: hashing uses stdlib PBKDF2 and the token is a
# hand-rolled HS256 JWT (stdlib hmac/hashlib/base64/json). That keeps the auth
# slice self-contained — no extra packages to install. If you later add
# passlib/PyJWT, swap the bodies here; the function signatures are the contract.

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User

# Secret used to sign tokens. MUST be overridden in production via env.
SECRET_KEY = os.getenv("AUTH_SECRET", "dev-insecure-secret-change-me")
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_TOKEN_TTL", str(60 * 60 * 24)))  # 24h

_PBKDF2_ITERATIONS = 200_000

# Extracts a "Authorization: Bearer <token>" header. tokenUrl is only used to
# render the Swagger "Authorize" button; our /auth/login accepts JSON.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password into a self-describing PBKDF2 string."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(_PBKDF2_ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(dk).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# --- tokens (HS256 JWT) -----------------------------------------------------

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def create_access_token(subject: str, expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
    """Create a signed HS256 JWT whose `sub` claim identifies the user."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "exp": now + expires_in}

    signing_input = (
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    )
    signature = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + _b64url_encode(signature)


def decode_access_token(token: str) -> Optional[dict]:
    """Return the token's payload if the signature is valid and it's unexpired."""
    try:
        header_seg, payload_seg, signature_seg = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_seg}.{payload_seg}"
    expected_sig = hmac.new(SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, _b64url_decode(signature_seg)):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_seg))
    except (ValueError, TypeError):
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    return payload


# --- current-user dependency ------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve and return the user named by a valid token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.execute(
        select(User).where(User.id == int(payload["sub"]))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_error

    return user
