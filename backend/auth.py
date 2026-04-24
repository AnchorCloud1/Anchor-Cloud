# ============================================================
# auth.py — Anchor Cloud Authentication Module
#
# Handles:
#   - JWT token creation and verification
#   - Current user extraction from Bearer token (FastAPI dep)
#   - Google OAuth 2.0 URL generation and callback handling
# ============================================================

from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import settings
from database import get_db, User
from crypto import verify_password

# ── JWT Setup ────────────────────────────────────────────────
BEARER_SCHEME = HTTPBearer()

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── Token Utilities ──────────────────────────────────────────

def create_access_token(user_id: str, extra: dict = None) -> str:
    """
    Creates a signed JWT access token.

    Payload:
      sub  : user_id
      exp  : expiry timestamp
      iat  : issued-at timestamp
      type : 'access'
      + any extra fields passed in
    """
    now    = datetime.utcnow()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MIN)

    payload = {
        "sub"  : user_id,
        "exp"  : expire,
        "iat"  : now,
        "type" : "access",
        **(extra or {}),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and verifies a JWT token.

    Returns:
        The decoded payload dict.

    Raises:
        HTTPException 401 if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type.")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI Dependency ───────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(BEARER_SCHEME),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — extracts and validates the Bearer token,
    then returns the corresponding User ORM object.

    Usage in route:
        @app.get("/protected")
        def protected(user: User = Depends(get_current_user)):
            ...
    """
    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")

    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


# ── Email / Phone Auth Helpers ───────────────────────────────

def authenticate_user(db: Session, identifier: str, password: str) -> Optional[User]:
    """
    Looks up a user by email OR phone number, then verifies
    the password using bcrypt.

    Returns the User if valid, None otherwise.
    """
    # Try email first
    user = db.query(User).filter(User.email == identifier.lower()).first()

    # Fallback to phone
    if not user:
        user = db.query(User).filter(User.phone == identifier).first()

    if not user:
        return None

    if not user.hashed_password:
        # OAuth-only account — no password set
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# ── Google OAuth 2.0 ─────────────────────────────────────────

def get_google_auth_url(state: str = "") -> str:
    """
    Builds the Google OAuth 2.0 authorization URL.
    Redirects the user to Google's consent screen.
    """
    params = {
        "client_id"    : settings.GOOGLE_CLIENT_ID,
        "redirect_uri" : settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope"        : "openid email profile",
        "access_type"  : "offline",
        "state"        : state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_google_code(code: str) -> dict:
    """
    Exchanges a Google authorization code for user info.

    Returns a dict with:
      google_id, email, name, avatar_url

    Raises:
        HTTPException 400 if the exchange fails.
    """
    # Step 1: Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code"          : code,
            "client_id"     : settings.GOOGLE_CLIENT_ID,
            "client_secret" : settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri"  : settings.GOOGLE_REDIRECT_URI,
            "grant_type"    : "authorization_code",
        })

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange Google auth code.")

    token_data   = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token in Google response.")

    # Step 2: Fetch user profile
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info.")

    info = user_resp.json()

    return {
        "google_id" : info.get("sub"),
        "email"     : info.get("email"),
        "name"      : info.get("name", info.get("email", "").split("@")[0]),
        "avatar_url": info.get("picture"),
    }