import base64
import hashlib
import secrets
from typing import Annotated

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .errors import ApiError
from .models import AccessToken, User, now_ms
from .schemas import AuthResult

Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def password_bytes(password: str) -> bytes:
    # SHA-256 prehash supports passwords longer than bcrypt's 72 byte limit.
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password_bytes(password), bcrypt.gensalt()).decode()


def verify_password(password: str, encoded: str) -> bool:
    return bcrypt.checkpw(password_bytes(password), encoded.encode())


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user: User) -> AuthResult:
    token = secrets.token_urlsafe(32)
    db.add(AccessToken(token_hash=token_digest(token), user_id=user.id,
                       expires_at=now_ms() + 7 * 24 * 60 * 60 * 1000))
    db.commit()
    return AuthResult(user=user, access_token=token)


def current_token(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    token = db.get(AccessToken, token_digest(credentials.credentials)) if credentials else None
    if token is None or token.expires_at <= now_ms():
        raise ApiError(401, "Missing, expired or invalid bearer token.", "auth")
    return token


Token = Annotated[AccessToken, Depends(current_token)]
