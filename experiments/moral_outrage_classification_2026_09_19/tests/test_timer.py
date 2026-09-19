"""Tests for the shared request timer."""

import time

import pytest

from shared.timer import timed


class TestTimed:
    """Tests for timed()."""

    def test_success_returns_result_and_latency(self) -> None:
        """A ~20ms call keeps its return value and reports latency in ms."""

        @timed
        def sleep_briefly() -> str:
            time.sleep(0.02)
            return "ok"

        result, latency_ms = sleep_briefly()

        assert result == "ok"
        assert latency_ms >= 15

    def test_exception_propagates(self) -> None:
        """ValueError from the wrapped function is not swallowed."""

        @timed
        def raise_value_error() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            raise_value_error()
