from typing import Dict, List, Sequence
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def encode_pooled_layers(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    device: torch.device,
    text: str,
    layer_indices: Sequence[int],
) -> List[np.ndarray]:
    inputs = tokenizer(text, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        out = model(**inputs, output_hidden_states=True, use_cache=False)
    hidden_states = out.hidden_states
    pooled: List[np.ndarray] = []
    for li in layer_indices:
        hs = hidden_states[li]  # [batch, seq, dim]
        last_token = hs[0, -1, :]
        pooled.append(last_token.detach().cpu().float().numpy())
    return pooled


def per_layer_zscore_across_concepts(
    layer_scores: Dict[str, List[float]],
    eps: float = 1e-8,
) -> Dict[str, List[float]]:
    """
    layer_scores: concept -> list over layers of raw dot-product scores
    Returns: concept -> list over layers of z-scored values
    """
    concepts = list(layer_scores.keys())
    num_layers = len(next(iter(layer_scores.values())))
    zscored: Dict[str, List[float]] = {c: [0.0] * num_layers for c in concepts}
    for li in range(num_layers):
        vals = np.array([layer_scores[c][li] for c in concepts], dtype=np.float64)
        mean = float(vals.mean())
        std = float(vals.std() + eps)
        for c in concepts:
            zscored[c][li] = (layer_scores[c][li] - mean) / std
    return zscored


def aggregate_scores(zscores: Dict[str, List[float]]) -> Dict[str, float]:
    return {c: float(np.mean(vs)) for c, vs in zscores.items()}


def minmax_normalize(scores: Dict[str, float], eps: float = 1e-8) -> Dict[str, float]:
    vals = np.array(list(scores.values()), dtype=np.float64)
    mn, mx = float(vals.min()), float(vals.max())
    denom = (mx - mn) if (mx - mn) > eps else 1.0
    return {k: (v - mn) / denom for k, v in scores.items()}


def score_text_against_concepts(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    device: torch.device,
    text: str,
    concept_vectors: Dict[str, List[np.ndarray]],
    layer_indices: Sequence[int],
) -> Dict[str, float]:
    pooled = encode_pooled_layers(model, tokenizer, device, text, layer_indices)
    layer_scores: Dict[str, List[float]] = {}
    for concept, vecs in concept_vectors.items():
        raw: List[float] = []
        for li, v in enumerate(vecs):
            s = float(np.dot(pooled[li], v))
            raw.append(s)
        layer_scores[concept] = raw
    z = per_layer_zscore_across_concepts(layer_scores)
    agg = aggregate_scores(z)
    rel = minmax_normalize(agg)
    return rel


