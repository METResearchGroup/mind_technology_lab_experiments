"""User-role vector math from Jeong et al., equations (1) and (2)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatVec = NDArray[np.floating]


def _as_2d(activations: NDArray[np.floating]) -> NDArray[np.floating]:
    array = np.asarray(activations, dtype=np.float64)
    if array.ndim == 1:
        return array.reshape(1, -1)
    if array.ndim != 2:
        raise ValueError("activations must be a 1D or 2D array")
    return array


def extract_user_role_vector(
    user_activations: NDArray[np.floating],
    assistant_activations: NDArray[np.floating],
) -> FloatVec:
    """Difference-in-means user-role direction (equation 1).

    Each row is one paired dialogue. The returned vector is the mean of
    user minus assistant hidden states at the chosen layer.
    """
    user = _as_2d(user_activations)
    assistant = _as_2d(assistant_activations)
    if user.shape != assistant.shape:
        raise ValueError("user and assistant activations must share a shape")
    if user.shape[0] == 0:
        raise ValueError("need at least one paired dialogue")
    return np.mean(user - assistant, axis=0)


def unit_vector(vector: NDArray[np.floating]) -> FloatVec:
    array = np.asarray(vector, dtype=np.float64).reshape(-1)
    norm = np.linalg.norm(array)
    if norm == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return array / norm


def steer_activation(
    hidden_state: NDArray[np.floating],
    role_vector: NDArray[np.floating],
    alpha: float,
) -> FloatVec:
    """Add a scaled unit role vector to a hidden state (equation 2).

    ``alpha`` is the steering strength. Negative values reverse the direction.
    """
    hidden = np.asarray(hidden_state, dtype=np.float64).reshape(-1)
    direction = unit_vector(role_vector)
    hidden_norm = float(np.linalg.norm(hidden))
    return hidden + alpha * hidden_norm * direction


def cosine_similarity(
    left: NDArray[np.floating],
    right: NDArray[np.floating],
) -> float:
    a = np.asarray(left, dtype=np.float64).reshape(-1)
    b = np.asarray(right, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        raise ValueError("vectors must have the same length")
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def project_onto_direction(
    hidden_state: NDArray[np.floating],
    role_vector: NDArray[np.floating],
) -> float:
    """Scalar projection of a hidden state onto the unit role direction."""
    hidden = np.asarray(hidden_state, dtype=np.float64).reshape(-1)
    direction = unit_vector(role_vector)
    return float(np.dot(hidden, direction))
