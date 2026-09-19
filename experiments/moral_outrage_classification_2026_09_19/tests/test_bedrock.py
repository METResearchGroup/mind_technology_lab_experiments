"""Mocked tests for the Bedrock engine."""

import pytest

from models.bedrock import BedrockEngine


class TestBedrockEngine:
    """Tests for BedrockEngine."""

    def test_luna_model_name(self) -> None:
        """Converse on the Luna profile uses the locked display name."""
        payload = {
            "output": {
                "message": {
                    "content": [
                        {"text": '{"moral_outrage": true, "probability": 0.88}'}
                    ]
                }
            },
            "usage": {"inputTokens": 20, "outputTokens": 8},
        }

        def converse(**_kwargs: object) -> dict[str, object]:
            return payload

        engine = BedrockEngine("us.openai.gpt-5.6-luna", converse=converse)
        result = engine.label_one("They cheated those families.")

        assert result.model_name == "Bedrock:us.openai.gpt-5.6-luna"
        assert result.probability == 0.88
        assert result.binary_label == 1

    def test_rejects_foundation_id_without_us_prefix(self) -> None:
        """anthropic.claude-sonnet-5 without the US profile prefix is rejected."""
        with pytest.raises(ValueError):
            BedrockEngine("anthropic.claude-sonnet-5")
