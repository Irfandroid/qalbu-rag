import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """Fixed-window IP limiter for one FastAPI process.

    Deploy behind a shared store/rate limiter before running multiple API replicas.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        with self._lock:
            recent = self._requests[key]
            while recent and current - recent[0] >= self.window_seconds:
                recent.popleft()
            if len(recent) >= self.max_requests:
                return False
            recent.append(current)
            return True
