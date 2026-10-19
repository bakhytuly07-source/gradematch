"""Owner-scoped in-memory Library containing only approved saved data."""
from threading import RLock
from time import time_ns
from uuid import uuid4

from .color import normalize_thumbnail
from .errors import ApiError
from .schemas import Look, RenameLookInput, SaveLookInput


class MemoryLooks:
    def __init__(self, *, clock=None):
        self.clock = clock if clock is not None else lambda: time_ns() // 1_000_000
        self._records: dict[str, tuple[str, Look]] = {}
        self._lock = RLock()

    def create(self, owner: str, body: SaveLookInput) -> Look:
        body = SaveLookInput.model_validate(body.model_dump(by_alias=True))
        thumbnail = normalize_thumbnail(body.thumbnail)
        timestamp = self.clock()
        look = Look(id=str(uuid4()), name=body.name.strip() or "Untitled look",
            style_params=body.style_params.model_copy(deep=True),
            adjustments=body.adjustments.model_copy(deep=True), thumbnail_url=thumbnail,
            is_favorite=False, created_at=timestamp, updated_at=timestamp)
        with self._lock:
            self._records[look.id] = (owner, look)
        return look.model_copy(deep=True)

    def _owned(self, owner: str, id: str) -> Look:
        record = self._records.get(id)
        if record is None or record[0] != owner:
            raise ApiError(404, "Look was not found.", "not_found")
        return record[1]

    def get(self, owner: str, id: str) -> Look:
        with self._lock:
            return self._owned(owner, id).model_copy(deep=True)

    def for_owner(self, owner: str) -> list[Look]:
        with self._lock:
            return [look.model_copy(deep=True) for user, look in self._records.values() if user == owner]

    # Preserve the already-existing get/rename/favorite routes in memory mode.
    def rename(self, owner: str, id: str, name: str) -> Look:
        name = RenameLookInput(name=name).name.strip()
        with self._lock:
            look = self._owned(owner, id)
            look.name = name
            look.updated_at = max(self.clock(), look.updated_at + 1)
            return look.model_copy(deep=True)

    def toggle_favorite(self, owner: str, id: str) -> Look:
        with self._lock:
            look = self._owned(owner, id)
            look.is_favorite = not look.is_favorite
            look.updated_at = max(self.clock(), look.updated_at + 1)
            return look.model_copy(deep=True)
