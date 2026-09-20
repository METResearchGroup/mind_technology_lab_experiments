"""Published numbers from arXiv:2609.07573, used as dashboard references."""

from __future__ import annotations

# Table 2: GPT-4.1-mini full-persona A-shares by group (percent).
PAPER_LLM_BY_GROUP: dict[str, dict[str, dict[str, float]]] = {
    "env_priority": {
        "sex": {"Male": 93, "Female": 99},
        "age_env": {"19-29": 96, "30-44": 96, "45-59": 96, "60+": 97},
        "education": {"middle": 91, "high": 96, "college": 98, "graduate": 99},
    },
    "env_means": {
        "sex": {"Male": 0, "Female": 1},
        "age_env": {"19-29": 0, "30-44": 0, "45-59": 1, "60+": 2},
        "education": {"middle": 0, "high": 1, "college": 0, "graduate": 2},
    },
    "clim_strategy": {
        "sex": {"Male": 88, "Female": 93},
        "age_env": {"19-29": 77, "30-44": 89, "45-59": 96, "60+": 99},
        "education": {"middle": 95, "high": 95, "college": 89, "graduate": 81},
    },
    "clim_tech": {
        "sex": {"Male": 73, "Female": 53},
        "age_env": {"19-29": 76, "30-44": 57, "45-59": 61, "60+": 59},
        "education": {"middle": 51, "high": 65, "college": 68, "graduate": 69},
    },
    "work_family": {
        "sex": {"Male": 100, "Female": 100},
        "age_birth": {"20s": 100, "30s": 100, "40s": 100},
        "marital": {"Single": 100, "Married": 100},
    },
    "educ_care": {
        "sex": {"Male": 55, "Female": 69},
        "age_birth": {"20s": 45, "30s": 73, "40s": 68},
        "marital": {"Single": 48, "Married": 68},
    },
    "econ_support": {
        "sex": {"Male": 22, "Female": 0},
        "age_birth": {"20s": 7, "30s": 8, "40s": 11},
        "marital": {"Single": 9, "Married": 14},
    },
    "housing": {
        "sex": {"Male": 31, "Female": 20},
        "age_birth": {"20s": 34, "30s": 33, "40s": 33},
        "marital": {"Single": 39, "Married": 18},
    },
}

# Table 3: overall A-share under persona-ablation controls.
PAPER_TABLE3: dict[str, dict[str, float]] = {
    "env_priority": {
        "full": 96,
        "demographics": 87,
        "citizen": 100,
        "none": 100,
        "human": 68,
    },
    "env_means": {
        "full": 1,
        "demographics": 34,
        "citizen": 1,
        "none": 1,
        "human": 54,
    },
    "clim_strategy": {
        "full": 90,
        "demographics": 65,
        "citizen": 6,
        "none": 6,
        "human": 70,
    },
    "clim_tech": {
        "full": 63,
        "demographics": 98,
        "citizen": 100,
        "none": 100,
        "human": 51,
    },
    "work_family": {
        "full": 100,
        "demographics": 100,
        "citizen": 79,
        "none": 82,
        "human": 61,
    },
    "educ_care": {
        "full": 62,
        "demographics": 71,
        "citizen": 28,
        "none": 30,
        "human": 58,
    },
    "econ_support": {
        "full": 11,
        "demographics": 9,
        "citizen": 0,
        "none": 0,
        "human": 56,
    },
    "housing": {
        "full": 26,
        "demographics": 3,
        "citizen": 8,
        "none": 9,
        "human": 53,
    },
}

# Table 6: mean agents on A after 3 rounds in balanced rooms (out of 6).
PAPER_TABLE6: list[dict[str, float | str]] = [
    {
        "question_id": "clim_tech",
        "debate_final_a": 4.3,
        "monologue_final_a": 4.0,
        "difference": 0.3,
    },
    {
        "question_id": "educ_care",
        "debate_final_a": 5.2,
        "monologue_final_a": 5.3,
        "difference": -0.2,
    },
    {
        "question_id": "env_priority",
        "debate_final_a": 5.2,
        "monologue_final_a": 4.8,
        "difference": 0.3,
    },
    {
        "question_id": "clim_strategy",
        "debate_final_a": 5.5,
        "monologue_final_a": 5.7,
        "difference": -0.2,
    },
    {
        "question_id": "econ_support",
        "debate_final_a": 0.3,
        "monologue_final_a": 1.3,
        "difference": -1.0,
    },
    {
        "question_id": "housing",
        "debate_final_a": 3.5,
        "monologue_final_a": 4.2,
        "difference": -0.7,
    },
]

# Table 7: survey-chosen, nothing vs position-restated (mean A count, % moved).
PAPER_TABLE7: list[dict[str, float | str]] = [
    {
        "question_id": "clim_tech",
        "nothing_a": 4.3,
        "nothing_move": 39,
        "restated_a": 2.8,
        "restated_move": 3,
    },
    {
        "question_id": "educ_care",
        "nothing_a": 5.2,
        "nothing_move": 36,
        "restated_a": 3.0,
        "restated_move": 0,
    },
    {
        "question_id": "env_priority",
        "nothing_a": 5.2,
        "nothing_move": 42,
        "restated_a": 3.0,
        "restated_move": 0,
    },
    {
        "question_id": "clim_strategy",
        "nothing_a": 5.5,
        "nothing_move": 42,
        "restated_a": 3.0,
        "restated_move": 0,
    },
    {
        "question_id": "econ_support",
        "nothing_a": 0.3,
        "nothing_move": 44,
        "restated_a": 2.8,
        "restated_move": 3,
    },
    {
        "question_id": "housing",
        "nothing_a": 3.5,
        "nothing_move": 53,
        "restated_a": 3.2,
        "restated_move": 3,
    },
]

PAPER_FINDINGS = [
    {
        "id": "representation",
        "title": "Persona answers miss the survey map",
        "body": (
            "On 640 census-balanced Korean personas, GPT-4.1-mini's mean "
            "absolute gap from human group shares is 29 points. Every "
            "demographic group's mean gap sits between 24 and 34 points."
        ),
    },
    {
        "id": "direction",
        "title": "Demographic direction is often reversed",
        "body": (
            "When the human survey has one group higher than another, the "
            "personas match that direction in 34 of 110 comparisons. On the "
            "two relatively split questions the match is 9 of 28."
        ),
    },
    {
        "id": "concentration",
        "title": "Answers pile up near 0% or 100%",
        "body": (
            "On five of eight questions at least one demographic group is "
            "near 0 or 100, while the matching human shares stay closer to "
            "the middle. Only climate technology (63%) and education-care "
            "(62%) stay inside the paper's 65% 'divisive' cutoff."
        ),
    },
    {
        "id": "interaction",
        "title": "Sealed monologues land in the same place",
        "body": (
            "In balanced rooms, the mean gap between full debate and sealed "
            "monologue final A counts is at most one agent out of six. Much "
            "of the observed stance movement can arise without peer exchange."
        ),
    },
    {
        "id": "anchor",
        "title": "Restating a starting side freezes updating",
        "body": (
            "When round 1 names the assigned side, movement falls to 0 to 3% "
            "in most cells. A fully argued opening is not required for that "
            "freeze. Anchoring population-informed starts also stalls updating."
        ),
    },
    {
        "id": "use",
        "title": "Treat argument surfacing as a separate job",
        "body": (
            "The transcripts still give reasons on both sides, and argument "
            "counts rise across rounds. That can help a reader inspect "
            "arguments. It does not show that the room represents a "
            "population, or that peer exchange caused the stance changes."
        ),
    },
]
