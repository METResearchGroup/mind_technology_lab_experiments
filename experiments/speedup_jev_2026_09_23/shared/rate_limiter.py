"""Thread-safe cap on request starts per rolling minute.

Run from the experiment folder:

    uv run python -c "from shared.rate_limiter import RequestStartLimiter; print(RequestStartLimiter.__name__)"
"""

from __future__ import annotations

import threading
import time
from collections import deque

MAX_REQUEST_STARTS_PER_MINUTE = 1000
WINDOW_SECONDS = 60.0


class RequestStartLimiter:
    """Block until one more request start fits in the rolling window."""

    def __init__(self, max_starts_per_minute: int) -> None:
        self._max_starts = max_starts_per_minute
        self._lock = threading.Lock()
        self._start_times: deque[float] = deque()

    def wait(self) -> None:
        """Wait until starting one more request stays within the cap."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._drop_expired(now)
                if len(self._start_times) < self._max_starts:
                    self._start_times.append(now)
                    return
                sleep_seconds = self._start_times[0] + WINDOW_SECONDS - now
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    def _drop_expired(self, now: float) -> None:
        window_start = now - WINDOW_SECONDS
        while self._start_times and self._start_times[0] <= window_start:
            self._start_times.popleft()
