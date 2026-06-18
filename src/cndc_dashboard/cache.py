"""Simple in-memory cache with per-key locks."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    updated_at: datetime
    source: str


class MemoryCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def get(self, key: str) -> CacheEntry | None:
        return self._entries.get(key)

    def invalidate(self) -> None:
        with self._global_lock:
            self._entries.clear()

    def get_or_load(self, key: str, ttl_seconds: int, loader: Callable[[], T]) -> CacheEntry[T]:
        now = datetime.now().astimezone()
        entry = self._entries.get(key)
        if entry and now - entry.updated_at <= timedelta(seconds=ttl_seconds):
            return entry
        lock = self._lock_for(key)
        with lock:
            now = datetime.now().astimezone()
            entry = self._entries.get(key)
            if entry and now - entry.updated_at <= timedelta(seconds=ttl_seconds):
                return entry
            value = loader()
            entry = CacheEntry(value=value, updated_at=now, source="API")
            self._entries[key] = entry
            return entry

    def _lock_for(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
