"""Request timer around one remote call.

Run from the experiment folder:

    uv run python -c "from shared.timer import timed; print(timed.__name__)"
"""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def timed(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """Wrap a remote call and return ``(result, latency_ms)``."""
    raise NotImplementedError
