# Canonical list of small, Mac-friendly HF model IDs for multi-model runs.
# Sources:
# - Qwen2.5-0.5B-Instruct: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
# - Qwen2.5-1.5B-Instruct: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
# - TinyLlama-1.1B-Chat-v1.0: https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0
# - EleutherAI pythia-1.4b: https://huggingface.co/EleutherAI/pythia-1.4b

ALLOWED_MODELS = [
    "Qwen/Qwen2.5-0.5B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "EleutherAI/pythia-1.4b",
]

def is_allowed(model_id: str) -> bool:
    return model_id in ALLOWED_MODELS


