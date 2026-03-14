import time
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    fetched_at: float

class TTLCache:
    def __init__(self):
        self._store: dict[str, CacheEntry] = {}

    # Get cache entry by key
    def get(self, key: str) -> Optional[CacheEntry]:
        return self._store.get(key)

    # Check if cache entry is fresh
    def is_fresh(self, key: str) -> bool:
        entry = self._store.get(key)
        return bool(entry) and time.time() < entry.expires_at

    # Set cache entry
    def set(self, key: str, value: Any, ttl_seconds: int) -> CacheEntry:
        now = time.time()
        entry = CacheEntry(value=value, fetched_at=now, expires_at=now + ttl_seconds)
        self._store[key] = entry
        return entry
