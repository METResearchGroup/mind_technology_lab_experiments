from typing import Dict, List, Tuple, Sequence
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def _encode_hidden_pooled(
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
    hidden_states = out.hidden_states  # tuple of length (num_layers+1)
    pooled: List[np.ndarray] = []
    for li in layer_indices:
        hs = hidden_states[li]  # [batch, seq, dim]
        last_token = hs[0, -1, :]  # [dim]
        pooled.append(last_token.detach().cpu().float().numpy())
    return pooled


def l2_normalize(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm < eps:
        return vec
    return vec / norm


def build_concept_vectors(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    device: torch.device,
    concept_pairs: Dict[str, List[Tuple[str, str]]],
    layer_indices: Sequence[int],
) -> Dict[str, List[np.ndarray]]:
    """
    Returns: dict concept -> list over layer_indices of normalized concept vectors (np.ndarray [dim])
    """
    concept_to_vectors: Dict[str, List[np.ndarray]] = {}
    for concept, pairs in concept_pairs.items():
        per_layer_vecs: List[np.ndarray] = []
        for li in layer_indices:
            diffs: List[np.ndarray] = []
            for pos, neg in pairs:
                h_pos = _encode_hidden_pooled(model, tokenizer, device, pos, [li])[0]
                h_neg = _encode_hidden_pooled(model, tokenizer, device, neg, [li])[0]
                diffs.append(h_pos - h_neg)
            mean_diff = np.mean(np.stack(diffs, axis=0), axis=0)
            per_layer_vecs.append(l2_normalize(mean_diff))
        concept_to_vectors[concept] = per_layer_vecs
    return concept_to_vectors


