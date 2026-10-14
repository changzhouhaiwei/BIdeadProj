from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        if not self.enabled:
            return True
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True
