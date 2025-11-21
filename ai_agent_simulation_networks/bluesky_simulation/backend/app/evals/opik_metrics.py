from functools import lru_cache
from typing import Dict, Any
from datetime import datetime
import opik
from opik.evaluation.metrics import Usefulness, Moderation, StructuredOutputCompliance


@lru_cache(maxsize=1)
def _usefulness_metric() -> Usefulness:
    return Usefulness(model="gpt-4o-mini")


@lru_cache(maxsize=1)
def _moderation_metric() -> Moderation:
    return Moderation(model="gpt-4o-mini")


@lru_cache(maxsize=1)
def _structure_metric() -> StructuredOutputCompliance:
    # structured outputs rely on JSON, which our prompts enforce
    return StructuredOutputCompliance(model="gpt-4o-mini")


def _metadata_timestamp() -> str:
    return datetime.now().strftime("%Y_%m_%d-%H:%M:%S")


def score_with_opik_metrics(
    agent_handle: str,
    turn: int,
    like_prompt: str,
    like_response: str,
    draft_prompt: str,
    draft_response: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Runs Opik's built-in evaluation metrics (Usefulness, Moderation, StructuredOutputCompliance)
    against the like and draft model outputs and records them in a dedicated span.
    """
    with opik.start_as_current_span(
        name="opik_metrics",
        type="eval",
        metadata={
            "agent_handle": agent_handle,
            "turn": turn,
            "session_id": session_id,
            "timestamp": _metadata_timestamp(),
        },
    ) as span:
        usefulness = _usefulness_metric()
        moderation = _moderation_metric()
        structure = _structure_metric()

        like_usefulness = usefulness.score(input=like_prompt, output=like_response)
        draft_usefulness = usefulness.score(input=draft_prompt, output=draft_response)

        like_moderation = moderation.score(input=like_prompt, output=like_response)
        draft_moderation = moderation.score(input=draft_prompt, output=draft_response)

        like_structure = structure.score(input=like_prompt, output=like_response)
        draft_structure = structure.score(input=draft_prompt, output=draft_response)

        result = {
            "agent_handle": agent_handle,
            "turn": turn,
            "usefulness": {
                "like": like_usefulness,
                "draft": draft_usefulness,
            },
            "moderation": {
                "like": like_moderation,
                "draft": draft_moderation,
            },
            "structured_output": {
                "like": like_structure,
                "draft": draft_structure,
            },
        }
        span.input = {
            "like_prompt": like_prompt,
            "draft_prompt": draft_prompt,
        }
        span.output = result
        return result


