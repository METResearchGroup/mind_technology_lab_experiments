"""Thread-safe cap on request starts per rolling minute.

Run from the experiment folder:

    uv run python -c "from shared.rate_limiter import RequestStartLimiter; print(RequestStartLimiter.__name__)"
"""

from __future__ import annotations

MAX_REQUEST_STARTS_PER_MINUTE = 1000


class RequestStartLimiter:
    """Block until one more request start fits in the rolling window."""

    def __init__(self, max_starts_per_minute: int) -> None:
        raise NotImplementedError

    def wait(self) -> None:
        """Wait until starting one more request stays within the cap."""
        raise NotImplementedError
