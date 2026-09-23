from __future__ import annotations

import math
import re
import zlib

import numpy as np

from lifemem.types import LifeEvent, RetrievedEvent, SurveyQuestion


def recency_weight(event_wave: int, current_wave: int, alpha: float) -> float:
    if alpha < 0:
        raise ValueError("forgetting alpha must be non-negative")
    return float(alpha ** max(current_wave - event_wave, 0))


def hashed_ngram_embed(text: str, dim: int = 128, n: int = 3) -> np.ndarray:
    """Deterministic encoder used when MiniLM/BGE weights are unavailable."""

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    blob = " ".join(tokens)
    vec = np.zeros(dim, dtype=np.float64)
    if len(blob) < n:
        grams = [blob] if blob else ["_"]
    else:
        grams = [blob[i : i + n] for i in range(len(blob) - n + 1)]
    for gram in grams:
        index = zlib.crc32(gram.encode("utf-8")) % dim
        vec[index] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm == 0:
        return vec
    return vec / norm


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    value = float(a @ b / denom)
    if math.isnan(value):
        return 0.0
    return value


class HashedEventEncoder:
    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def encode(self, text: str) -> np.ndarray:
        return hashed_ngram_embed(text, dim=self.dim)


def retrieve_events(
    query: SurveyQuestion,
    events: list[LifeEvent],
    current_wave: int,
    top_k: int,
    alpha: float,
    encoder: HashedEventEncoder | None = None,
) -> list[RetrievedEvent]:
    if not events:
        return []
    encoder = encoder or HashedEventEncoder()
    query_vec = encoder.encode(query.question)
    scored: list[RetrievedEvent] = []
    for event in events:
        sim = cosine(query_vec, encoder.encode(event.retrieval_text()))
        recency = recency_weight(event.wave, current_wave, alpha)
        scored.append(
            RetrievedEvent(
                event=event,
                semantic_similarity=sim,
                recency_weight=recency,
                final_score=float(sim * recency),
            )
        )
    scored.sort(key=lambda item: item.final_score, reverse=True)
    return scored[:top_k]
