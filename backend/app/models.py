from time import time_ns
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, ForeignKey, JSON, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column, validates, Session

from .database import Base


def now_ms() -> int:
    return time_ns() // 1_000_000


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now_ms)


    @validates("email")
    def normalize_email(self, key, value):
        return value.strip().lower()


class AccessToken(Base):
    __tablename__ = "access_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger)


class Look(Base):
    __tablename__ = "looks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    style_params: Mapped[dict] = mapped_column(JSON)
    adjustments: Mapped[dict] = mapped_column(JSON)
    thumbnail_url: Mapped[str] = mapped_column(Text, default="")
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


@event.listens_for(Session, "before_flush")
def validate_saved_looks(session, flush_context, instances):
    # Portable owner validation also works on engines that do not enforce FKs.
    from .color import normalize_thumbnail
    from .schemas import LutSettings
    for look in session.new.union(session.dirty):
        if not isinstance(look, Look):
            continue
        if look in session.new or inspect(look).attrs.user_id.history.has_changes():
            pending_owner = any(isinstance(user, User) and user.id == look.user_id
                                for user in session.new)
            if not pending_owner and session.get(User, look.user_id) is None:
                raise ValueError("Look owner must exist")
        if look in session.new or inspect(look).attrs.thumbnail_url.history.has_changes():
            look.thumbnail_url = normalize_thumbnail(look.thumbnail_url or "")
        settings = LutSettings(styleParams=look.style_params, adjustments=look.adjustments)
        look.style_params = settings.style_params.model_dump(by_alias=True)
        look.adjustments = settings.adjustments.model_dump()
