from __future__ import annotations

import pytest
from lifemem.config import LifeMemConfig
from lifemem.metrics import (
    kl_divergence,
    pairwise_categorical_distance,
    summarize_method,
)
from lifemem.parse import parse_option_code
from lifemem.retrieval import hashed_ngram_embed, recency_weight, retrieve_events
from lifemem.types import GenerationRecord, LifeEvent, SurveyOption, SurveyQuestion


def _question() -> SurveyQuestion:
    return SurveyQuestion(
        variable="LIFESAT",
        section="Wellbeing",
        question="You are satisfied with your life as a whole.",
        options=(
            SurveyOption("1", "Strongly disagree"),
            SurveyOption("2", "Disagree"),
            SurveyOption("3", "Neither"),
            SurveyOption("4", "Agree"),
            SurveyOption("5", "Strongly agree"),
        ),
    )


def _event(event_id: str, wave: int, text: str) -> LifeEvent:
    return LifeEvent(
        event_id=event_id,
        agent_id="A000",
        wave=wave,
        section="Work",
        question=text,
        answer_code="4",
        answer_text="Often",
        statement=f"You {text.lower()}",
        first_person=f"I {text.lower()}",
        tags=("work",),
    )


def test_parse_option_code() -> None:
    assert parse_option_code("4", ("1", "2", "3", "4", "5")) == "4"
    assert parse_option_code("Answer: 2.", ("1", "2", "3")) == "2"
    assert parse_option_code("nope", ("1", "2")) is None


def test_pairwise_distance_formula() -> None:
    assert pairwise_categorical_distance(["1", "1", "2"]) == pytest.approx(2 / 3)


def test_recency_matches_paper_alpha() -> None:
    # Paper reports λ = 0.105; configs use alpha = 0.9 = exp(-λ).
    assert recency_weight(1, 6, 0.9) == 0.9**5
    assert abs(0.9 - __import__("math").exp(-0.105)) < 1e-3


def test_hashed_encoder_is_deterministic() -> None:
    a = hashed_ngram_embed("You answered 'Often' to a promotion question.")
    b = hashed_ngram_embed("You answered 'Often' to a promotion question.")
    assert (a == b).all()
    assert abs(float((a**2).sum()) - 1.0) < 1e-9


def test_retrieval_prefers_recent_and_relevant() -> None:
    question = _question()
    events = [
        _event("old-job", 1, "Have you been unemployed and looking for work?"),
        _event("new-job", 6, "Have you been promoted at work?"),
        _event("sleep", 6, "How often have you had trouble sleeping?"),
    ]
    ranked = retrieve_events(question, events, current_wave=6, top_k=2, alpha=0.9)
    assert len(ranked) == 2
    assert ranked[0].final_score >= ranked[1].final_score
    assert ranked[0].event.wave == 6


def test_kl_is_zero_for_identical_distributions() -> None:
    import numpy as np

    p = np.array([0.2, 0.3, 0.5])
    assert kl_divergence(p, p) == 0.0


def test_summarize_method_returns_core_metrics() -> None:
    question = _question()
    records = [
        GenerationRecord(
            agent_id="A000",
            wave=1,
            variable="LIFESAT",
            human_answer="4",
            parsed_answer="4",
            valid_options=question.option_codes,
            method="lifemem",
            identity_groups={
                "ses": "low",
                "sex": "female",
                "education": "high school",
                "religion": "none",
            },
        ),
        GenerationRecord(
            agent_id="A001",
            wave=1,
            variable="LIFESAT",
            human_answer="2",
            parsed_answer="3",
            valid_options=question.option_codes,
            method="lifemem",
            identity_groups={
                "ses": "low",
                "sex": "male",
                "education": "high school",
                "religion": "none",
            },
        ),
    ]
    summary = summarize_method(records, LifeMemConfig().group_variables)
    assert summary["kl"] is not None
    assert summary["kl"] >= 0
    assert summary["n_records"] == 2
