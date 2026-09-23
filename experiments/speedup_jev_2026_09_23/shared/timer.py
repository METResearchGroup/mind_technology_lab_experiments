"""Request timer around one remote call.

Run from the experiment folder:

    uv run python -c "from shared.timer import timed; print(timed.__name__)"
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")

MS_PER_SECOND = 1000.0


def timed(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """Wrap a remote call and return ``(result, latency_ms)``.

    Exceptions are re-raised. Failed calls attach ``latency_ms`` on the
    exception when possible.
    """

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> tuple[T, float]:
        """Call ``func`` and return its result with elapsed milliseconds."""
        started = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            exc.latency_ms = (time.perf_counter() - started) * MS_PER_SECOND
            raise
        latency_ms = (time.perf_counter() - started) * MS_PER_SECOND
        return result, latency_ms

    return wrapper
