from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LifeMemConfig:
    """Paper defaults from Table 7 and the implementation appendix."""

    seed: int = 42
    top_k: int = 5
    forgetting_alpha: float = 0.9
    retrieval_eps: float = 1e-9
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    lora_target_modules: tuple[str, ...] = ("q_proj", "v_proj", "o_proj", "down_proj")
    learning_rate: float = 1e-4
    epochs_per_update: int = 2
    train_batch_size: int = 16
    replay_size: int = 4
    replay_weight: float = 0.5
    stability_weight: float = 0.01
    max_grad_norm: float = 1.0
    max_new_tokens: int = 16
    temperature: float = 0.0
    model_name: str = "Qwen/Qwen3.5-4B"
    disable_thinking: bool = True
    group_variables: tuple[str, ...] = ("sex", "ses", "education", "religion")
    methods: tuple[str, ...] = (
        "direct",
        "profile",
        "anti_stereotype",
        "full_history",
        "event_rag",
        "random_event",
        "lifemem",
        "lifemem_no_param",
        "lifemem_no_struct",
    )
    full_history_char_budget: int = 3 * 4096
    encoder_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    event_rag_encoder_name: str = "BAAI/bge-m3"
    use_hashed_encoder: bool = True
    hashed_dim: int = 128
    extra_method_notes: dict[str, str] = field(default_factory=dict)
