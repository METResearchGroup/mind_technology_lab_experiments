from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lifemem.config import LifeMemConfig
from lifemem.generators import update_parametric
from lifemem.types import AgentState, LifeEvent


@dataclass
class LoRAUpdateStats:
    training_steps: int
    mean_loss: float | None
    num_events: int
    num_replay_events: int


def build_event_training_examples(event: LifeEvent) -> list[dict[str, str]]:
    return [
        {"user": event.question, "assistant": event.answer_text, "type": "qa_binding"},
        {
            "user": f"Recall the following personal information:\n{event.statement}",
            "assistant": event.first_person,
            "type": "event_reconstruction",
        },
    ]


def inject_events_heuristic(
    agent: AgentState,
    events: list[LifeEvent],
    replay_events: list[LifeEvent],
    encoder: Any,
) -> LoRAUpdateStats:
    update_parametric(agent, events, replay_events, encoder)
    return LoRAUpdateStats(
        training_steps=2 * (len(events) + len(replay_events)),
        mean_loss=None,
        num_events=len(events),
        num_replay_events=len(replay_events),
    )


def lora_config_dict(config: LifeMemConfig) -> dict[str, Any]:
    return {
        "rank": config.lora_rank,
        "alpha": config.lora_alpha,
        "dropout": config.lora_dropout,
        "target_modules": list(config.lora_target_modules),
        "learning_rate": config.learning_rate,
        "epochs_per_event": config.epochs_per_update,
        "batch_size": config.train_batch_size,
        "max_train_seq_len": config.max_train_seq_len,
        "generate_batch_size": config.generate_batch_size,
        "max_generate_seq_len": config.max_generate_seq_len,
        "replay_size": config.replay_size,
        "replay_weight": config.replay_weight,
        "stability_weight": config.stability_weight,
        "max_grad_norm": config.max_grad_norm,
        "model_name": config.model_name,
        "disable_thinking": config.disable_thinking,
    }
