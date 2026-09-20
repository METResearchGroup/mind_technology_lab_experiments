"""Contrastive user-role vector extraction from Jeong et al. (arXiv:2609.00608)."""

from user_role_vector.caa import (
    cosine_similarity,
    extract_user_role_vector,
    project_onto_direction,
    steer_activation,
)
from user_role_vector.dialogues import (
    TOPIC_CATEGORIES,
    filter_dialogues,
    stratified_sample,
)
from user_role_vector.disengage import (
    disengagement_distance,
    disengagement_rate,
    exact_match_rate,
    first_disengage_turn,
)
from user_role_vector.reflections import (
    PROMPT_VARIANTS,
    average_role_activations,
    build_reflection_prompt,
    pair_role_activations,
    retain_valid_reflections,
)
from user_role_vector.style import score_user_likeness

__all__ = [
    "TOPIC_CATEGORIES",
    "PROMPT_VARIANTS",
    "average_role_activations",
    "build_reflection_prompt",
    "cosine_similarity",
    "disengagement_distance",
    "disengagement_rate",
    "exact_match_rate",
    "extract_user_role_vector",
    "filter_dialogues",
    "first_disengage_turn",
    "pair_role_activations",
    "project_onto_direction",
    "retain_valid_reflections",
    "score_user_likeness",
    "steer_activation",
    "stratified_sample",
]
