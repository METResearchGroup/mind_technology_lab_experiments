"""Mocked tests for the Perspective MORAL_OUTRAGE engine."""

import pytest

from models.perspective_api import (
    MoralOutrageAttributeRejected,
    PerspectiveApiEngine,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, object]:
        return self._payload


class TestPerspectiveApiEngineLabelOne:
    """Tests for PerspectiveApiEngine.label_one()."""

    def test_maps_summary_score(self) -> None:
        """summaryScore 0.12 yields Perspective API, binary 0, and cost 0."""
        payload = {
            "attributeScores": {
                "MORAL_OUTRAGE": {"summaryScore": {"value": 0.12}},
            }
        }

        def http_post(*_args: object, **_kwargs: object) -> _FakeResponse:
            return _FakeResponse(200, payload)

        engine = PerspectiveApiEngine(
            http_post=http_post, api_key="test", sleeper=lambda _seconds: None
        )

        result = engine.label_one("The cafe opens at nine.")

        assert result.model_name == "Perspective API"
        assert result.probability == 0.12
        assert result.binary_label == 0
        assert result.estimated_cost_usd == 0.0

    def test_unknown_attribute_raises(self) -> None:
        """HTTP 400 mentioning MORAL_OUTRAGE raises MoralOutrageAttributeRejected."""

        def http_post(*_args: object, **_kwargs: object) -> _FakeResponse:
            return _FakeResponse(400, {"error": "unknown attribute MORAL_OUTRAGE"})

        engine = PerspectiveApiEngine(
            http_post=http_post, api_key="test", sleeper=lambda _seconds: None
        )

        with pytest.raises(MoralOutrageAttributeRejected):
            engine.label_one("example")
