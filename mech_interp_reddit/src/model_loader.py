from typing import Tuple
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_qwen_15b(model_name: str = "Qwen/Qwen2.5-1.5B-Instruct") -> Tuple[AutoModelForCausalLM, AutoTokenizer, torch.device]:
    device = get_device()
    dtype = torch.float16 if device.type in ("mps", "cuda") else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, device_map=None)
    model.to(device)
    model.eval()
    return model, tokenizer, device


