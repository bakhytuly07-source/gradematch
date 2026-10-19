"""Injectable, isolated in-memory account repository."""
from dataclasses import dataclass, field
from threading import RLock
from time import time_ns
from uuid import uuid4

from .errors import ApiError
from .passwords import hash_password, verify_password
from .schemas import User


@dataclass(frozen=True)
class Account:
    id: str
    email: str
    password_hash: str = field(repr=False)
    created_at: int

    def public(self) -> User:
        return User(id=self.id, email=self.email)


class MemoryUsers:
    def __init__(self):
        self._by_id: dict[str, Account] = {}
        self._by_email: dict[str, Account] = {}
        self._lock = RLock()

    @staticmethod
    def normalize(email: str) -> str:
        return email.strip().lower()

    def create(self, email: str, password: str) -> Account:
        email = self.normalize(email)
        with self._lock:
            if email in self._by_email:
                raise ApiError(409, "An account with this email already exists.")
            user = Account(str(uuid4()), email, hash_password(password), time_ns() // 1_000_000)
            self._by_id[user.id] = user
            self._by_email[email] = user
            return user

    def get(self, id: str) -> Account | None:
        with self._lock:
            return self._by_id.get(id)

    def find(self, email: str) -> Account | None:
        with self._lock:
            return self._by_email.get(self.normalize(email))

    def authenticate(self, email: str, password: str) -> Account | None:
        user = self.find(email)
        if user is not None and verify_password(password, user.password_hash):
            return user
        return None


class OrmUsers:
    """Request-scoped account repository; the caller owns the transaction."""
    def __init__(self, db):
        self.db = db

    def create(self, email, password):
        from sqlalchemy.exc import IntegrityError
        from .models import User as UserModel
        user = UserModel(email=email, password_hash=hash_password(password))
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ApiError(409, "An account with this email already exists.") from None
        return user

    def authenticate(self, email, password):
        from sqlalchemy import select
        from .models import User as UserModel
        user = self.db.scalar(select(UserModel).where(UserModel.email == MemoryUsers.normalize(email)))
        return user if user is not None and verify_password(password, user.password_hash) else None
