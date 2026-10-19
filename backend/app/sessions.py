"""In-memory bearer sessions: only token hashes are retained."""
from dataclasses import dataclass
import hashlib
import secrets
from threading import RLock
from time import time_ns


@dataclass(frozen=True)
class SessionRecord:
    token_hash: str
    user_id: str
    expires_at: int


class MemorySessions:
    def __init__(self, *, clock=None, ttl_ms=7 * 24 * 60 * 60 * 1000):
        self.clock = clock if clock is not None else lambda: time_ns() // 1_000_000
        self.ttl_ms = ttl_ms
        self._tokens: dict[str, SessionRecord] = {}
        self._lock = RLock()

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def issue(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        digest = self.digest(token)
        with self._lock:
            self._tokens[digest] = SessionRecord(digest, user_id, self.clock() + self.ttl_ms)
        return token

    def resolve(self, token: str) -> SessionRecord | None:
        digest = self.digest(token)
        with self._lock:
            record = self._tokens.get(digest)
            if record is not None and record.expires_at <= self.clock():
                del self._tokens[digest]
                return None
            return record

    def revoke(self, record: SessionRecord) -> None:
        with self._lock:
            self._tokens.pop(record.token_hash, None)
