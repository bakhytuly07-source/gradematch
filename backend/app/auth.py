import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .errors import ApiError
from .models import AccessToken, User, now_ms
from .schemas import AuthResult
from .passwords import hash_password, verify_password

Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user: User) -> AuthResult:
    token = secrets.token_urlsafe(32)
    db.add(AccessToken(token_hash=token_digest(token), user_id=user.id,
                       expires_at=now_ms() + 7 * 24 * 60 * 60 * 1000))
    db.commit()
    return AuthResult(user=user, access_token=token)


def current_token(db: Db, request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    memory = request.app.state.memory
    if memory is not None:
        token = memory.sessions.resolve(credentials.credentials) if credentials else None
    else:
        token = db.get(AccessToken, token_digest(credentials.credentials)) if credentials else None
    if token is None or (memory is None and token.expires_at <= now_ms()):
        raise ApiError(401, "Missing, expired or invalid bearer token.", "auth")
    return token


Token = Annotated[AccessToken, Depends(current_token)]
