"""Published PRISK numbers transcribed from arXiv:2608.28833 Table 2."""

from __future__ import annotations

from typing import Any

# Resistance percentages. Lower = larger behavioral change under personalization.
PAPER_TABLE_2: list[dict[str, Any]] = [
    {
        "model": "GPT-5.4-mini",
        "irp": {
            "base": 100,
            "profile_only": 97.3,
            "retrieval_only": 100,
            "profile_retrieval": 96.5,
            "avg": 98.5,
        },
        "uir": {
            "base": 86.5,
            "profile_only": 46.9,
            "retrieval_only": 85.1,
            "profile_retrieval": 39.1,
            "avg": 64.4,
        },
        "syco": {
            "base": 99.5,
            "profile_only": 64.6,
            "retrieval_only": 71.9,
            "profile_retrieval": 20.3,
            "avg": 64.1,
        },
    },
    {
        "model": "GPT-5.4",
        "irp": {
            "base": 100,
            "profile_only": 86.3,
            "retrieval_only": 100,
            "profile_retrieval": 86.0,
            "avg": 93.1,
        },
        "uir": {
            "base": 87.4,
            "profile_only": 34.2,
            "retrieval_only": 66.4,
            "profile_retrieval": 35.1,
            "avg": 55.8,
        },
        "syco": {
            "base": 76.2,
            "profile_only": 10.3,
            "retrieval_only": 72.9,
            "profile_retrieval": 20.5,
            "avg": 45.0,
        },
    },
    {
        "model": "Claude Haiku 4.5",
        "irp": {
            "base": 100,
            "profile_only": 12.0,
            "retrieval_only": 99.6,
            "profile_retrieval": 15.6,
            "avg": 56.8,
        },
        "uir": {
            "base": 83.0,
            "profile_only": 35.1,
            "retrieval_only": 41.5,
            "profile_retrieval": 30.6,
            "avg": 47.6,
        },
        "syco": {
            "base": 52.1,
            "profile_only": 6.4,
            "retrieval_only": 50.6,
            "profile_retrieval": 1.4,
            "avg": 27.7,
        },
    },
    {
        "model": "Claude Sonnet 4.6",
        "irp": {
            "base": 100,
            "profile_only": 26.5,
            "retrieval_only": 99.3,
            "profile_retrieval": 33.8,
            "avg": 64.9,
        },
        "uir": {
            "base": 86.2,
            "profile_only": 40.1,
            "retrieval_only": 46.4,
            "profile_retrieval": 34.8,
            "avg": 51.9,
        },
        "syco": {
            "base": 49.0,
            "profile_only": 1.2,
            "retrieval_only": 52.1,
            "profile_retrieval": 12.4,
            "avg": 28.7,
        },
    },
    {
        "model": "Gemini 2.5 Flash Lite",
        "irp": {
            "base": 100,
            "profile_only": 47.6,
            "retrieval_only": 99.7,
            "profile_retrieval": 51.7,
            "avg": 74.8,
        },
        "uir": {
            "base": 84.1,
            "profile_only": 49.5,
            "retrieval_only": 65.3,
            "profile_retrieval": 36.6,
            "avg": 58.9,
        },
        "syco": {
            "base": 99.8,
            "profile_only": 38.0,
            "retrieval_only": 98.4,
            "profile_retrieval": 24.1,
            "avg": 65.1,
        },
    },
    {
        "model": "Gemini 2.5 Flash",
        "irp": {
            "base": 100,
            "profile_only": 79.8,
            "retrieval_only": 100,
            "profile_retrieval": 79.1,
            "avg": 89.7,
        },
        "uir": {
            "base": 77.8,
            "profile_only": 47.1,
            "retrieval_only": 48.2,
            "profile_retrieval": 46.9,
            "avg": 55.0,
        },
        "syco": {
            "base": 99.8,
            "profile_only": 59.5,
            "retrieval_only": 41.4,
            "profile_retrieval": 14.9,
            "avg": 53.9,
        },
    },
    {
        "model": "Gemini 2.5 Pro",
        "irp": {
            "base": 99.4,
            "profile_only": 10.7,
            "retrieval_only": 98.6,
            "profile_retrieval": 21.5,
            "avg": 57.6,
        },
        "uir": {
            "base": 71.3,
            "profile_only": 37.0,
            "retrieval_only": 54.4,
            "profile_retrieval": 22.1,
            "avg": 46.2,
        },
        "syco": {
            "base": 55.1,
            "profile_only": 0.9,
            "retrieval_only": 44.8,
            "profile_retrieval": 0.4,
            "avg": 25.3,
        },
    },
    {
        "model": "Llama 3.1 8B",
        "irp": {
            "base": 100,
            "profile_only": 40.1,
            "retrieval_only": 84.8,
            "profile_retrieval": 52.1,
            "avg": 69.2,
        },
        "uir": {
            "base": 78.9,
            "profile_only": 36.4,
            "retrieval_only": 37.2,
            "profile_retrieval": 38.1,
            "avg": 47.7,
        },
        "syco": {
            "base": 99.5,
            "profile_only": 37.2,
            "retrieval_only": 59.0,
            "profile_retrieval": 35.1,
            "avg": 57.7,
        },
    },
    {
        "model": "Llama 3.1 70B",
        "irp": {
            "base": 100,
            "profile_only": 45.5,
            "retrieval_only": 95.4,
            "profile_retrieval": 49.6,
            "avg": 72.6,
        },
        "uir": {
            "base": 80.0,
            "profile_only": 40.6,
            "retrieval_only": 44.4,
            "profile_retrieval": 37.3,
            "avg": 50.6,
        },
        "syco": {
            "base": 99.8,
            "profile_only": 40.1,
            "retrieval_only": 87.4,
            "profile_retrieval": 39.5,
            "avg": 66.7,
        },
    },
    {
        "model": "Qwen3-4B",
        "irp": {
            "base": 100,
            "profile_only": 46.8,
            "retrieval_only": 92.2,
            "profile_retrieval": 47.0,
            "avg": 71.5,
        },
        "uir": {
            "base": 83.5,
            "profile_only": 45.1,
            "retrieval_only": 51.3,
            "profile_retrieval": 43.4,
            "avg": 55.8,
        },
        "syco": {
            "base": 99.3,
            "profile_only": 26.1,
            "retrieval_only": 89.0,
            "profile_retrieval": 43.4,
            "avg": 64.5,
        },
    },
    {
        "model": "Qwen3-8B",
        "irp": {
            "base": 100,
            "profile_only": 55.5,
            "retrieval_only": 89.4,
            "profile_retrieval": 54.3,
            "avg": 74.8,
        },
        "uir": {
            "base": 78.7,
            "profile_only": 49.8,
            "retrieval_only": 61.1,
            "profile_retrieval": 50.7,
            "avg": 60.1,
        },
        "syco": {
            "base": 100,
            "profile_only": 36.6,
            "retrieval_only": 79.5,
            "profile_retrieval": 36.4,
            "avg": 63.1,
        },
    },
    {
        "model": "Qwen3-14B",
        "irp": {
            "base": 100,
            "profile_only": 53.0,
            "retrieval_only": 90.0,
            "profile_retrieval": 53.9,
            "avg": 74.2,
        },
        "uir": {
            "base": 81.6,
            "profile_only": 52.9,
            "retrieval_only": 61.0,
            "profile_retrieval": 50.7,
            "avg": 61.6,
        },
        "syco": {
            "base": 100,
            "profile_only": 34.3,
            "retrieval_only": 69.5,
            "profile_retrieval": 35.3,
            "avg": 59.8,
        },
    },
    {
        "model": "Qwen3-32B",
        "irp": {
            "base": 100,
            "profile_only": 60.0,
            "retrieval_only": 91.4,
            "profile_retrieval": 61.5,
            "avg": 78.2,
        },
        "uir": {
            "base": 77.8,
            "profile_only": 50.4,
            "retrieval_only": 53.0,
            "profile_retrieval": 48.9,
            "avg": 57.5,
        },
        "syco": {
            "base": 100,
            "profile_only": 46.5,
            "retrieval_only": 58.0,
            "profile_retrieval": 44.9,
            "avg": 62.4,
        },
    },
]

PAPER_BENCHMARK_ACCURACY = [
    {
        "model": "Gemini 2.5 Flash",
        "gsm8k_base": 87.9,
        "gsm8k_profile": 83.6,
        "csqa_base": 88.0,
        "csqa_profile": 86.0,
        "mmlu_base": 88.4,
        "mmlu_profile": 85.0,
    },
    {
        "model": "GPT-5.4 Mini",
        "gsm8k_base": 93.1,
        "gsm8k_profile": 92.6,
        "csqa_base": 90.2,
        "csqa_profile": 91.2,
        "mmlu_base": 91.0,
        "mmlu_profile": 90.4,
    },
    {
        "model": "Claude Haiku 4.5",
        "gsm8k_base": 92.2,
        "gsm8k_profile": 89.0,
        "csqa_base": 83.5,
        "csqa_profile": 84.0,
        "mmlu_base": 82.4,
        "mmlu_profile": 80.0,
    },
]


def paper_mean_drops() -> dict[str, float]:
    """Average base→profile drop across the 13 models, as percentages."""
    irp: list[float] = []
    uir: list[float] = []
    syco: list[float] = []
    for row in PAPER_TABLE_2:
        irp.append(row["irp"]["base"] - row["irp"]["profile_only"])
        uir.append(row["uir"]["base"] - row["uir"]["profile_only"])
        syco.append(row["syco"]["base"] - row["syco"]["profile_only"])
    return {
        "irp_drop_pct": round(sum(irp) / len(irp), 1),
        "uir_drop_pct": round(sum(uir) / len(uir), 1),
        "syco_drop_pct": round(sum(syco) / len(syco), 1),
        "n_models": len(PAPER_TABLE_2),
    }
