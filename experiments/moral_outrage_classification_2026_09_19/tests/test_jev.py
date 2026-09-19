"""Mocked tests for the TypeSafe Jev engine."""

from types import SimpleNamespace

from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS
from models.jev import JEV_QUESTION_ID, JevEngine


class _FakeTypeSafeClient:
    def __init__(self) -> None:
        self.state = None
        self.questions = None
        self.model = None

    def system_one(self, state: object, questions: object, model: str) -> object:
        self.state = state
        self.questions = questions
        self.model = model
        return SimpleNamespace(
            answers={JEV_QUESTION_ID: SimpleNamespace(noul=0.91)},
            usage=SimpleNamespace(input_tokens=11, output_tokens=3),
        )


class TestJevEngineLabelOne:
    """Tests for JevEngine.label_one()."""

    def test_maps_noul_to_prediction(self) -> None:
        """noul 0.91 yields Jev, probability 0.91, and binary_label 1."""
        engine = JevEngine(client=_FakeTypeSafeClient())

        result = engine.label_one("They should be punished.")

        assert result.model_name == "Jev"
        assert result.probability == 0.91
        assert result.binary_label == 1
        assert result.latency_ms >= 0

    def test_uses_shared_brady_instructions(self) -> None:
        """The Noul question uses the shared Brady instruction string."""
        client = _FakeTypeSafeClient()
        engine = JevEngine(client=client)

        engine.label_one("example")

        question = client.questions[JEV_QUESTION_ID]
        assert question.instructions == BRADY_MORAL_OUTRAGE_INSTRUCTIONS
