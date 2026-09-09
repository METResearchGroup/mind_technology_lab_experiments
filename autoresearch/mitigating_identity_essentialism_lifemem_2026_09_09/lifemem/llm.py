from __future__ import annotations

from typing import Any

import numpy as np

from lifemem.config import LifeMemConfig
from lifemem.lora_memory import build_event_training_examples
from lifemem.types import AgentState, LifeEvent, RetrievedEvent, SurveyQuestion

USER_CONTENT_KEY = "text"


def user_message(text: str) -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", USER_CONTENT_KEY: text}]}


def assistant_message(text: str) -> dict[str, Any]:
    return {"role": "assistant", "content": [{"type": "text", USER_CONTENT_KEY: text}]}


def infer_lora_targets(model: Any, preferred: tuple[str, ...]) -> list[str] | str:
    names = {
        name.rsplit(".", 1)[-1]
        for name, module in model.named_modules()
        if getattr(getattr(module, "weight", None), "ndim", 0) == 2
    }
    hit = [name for name in preferred if name in names]
    return hit or "all-linear"


def _chat_kwargs(disable_thinking: bool) -> dict[str, Any]:
    return {"enable_thinking": not disable_thinking, "tokenize": False}


class QwenRespondent:
    """Qwen3.5-4B respondent with per-(method, agent) PEFT LoRA adapters."""

    def __init__(self, config: LifeMemConfig | None = None) -> None:
        self.config = config or LifeMemConfig()
        self.model: Any = None
        self.processor: Any = None
        self.tokenizer: Any = None
        self.device: Any = None
        self._peft = False
        self._adapters: set[str] = set()
        self._load()

    def _load(self) -> None:
        import torch
        from transformers import (
            AutoModelForImageTextToText,
            AutoProcessor,
            AutoTokenizer,
        )

        dtype = (
            torch.bfloat16
            if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8
            else torch.float16
            if torch.cuda.is_available()
            else torch.float32
        )
        name = self.config.model_name
        self.processor = AutoProcessor.from_pretrained(name, trust_remote_code=True)
        self.tokenizer = getattr(self.processor, "tokenizer", None)
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
        self.model = AutoModelForImageTextToText.from_pretrained(
            name,
            dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )
        if not torch.cuda.is_available():
            self.model = self.model.to("cpu")
        self.model.eval()
        self.device = next(self.model.parameters()).device

    def train_adapter(
        self,
        method: str,
        agent: AgentState,
        events: list[LifeEvent],
        replay: list[LifeEvent],
    ) -> None:
        examples: list[dict[str, str]] = []
        for event in list(events) + list(replay):
            examples.extend(build_event_training_examples(event))
        if not examples:
            return
        adapter = _adapter_name(method, agent.profile.agent_id)
        self._ensure_adapter(adapter)
        self._fit(adapter, examples)

    def generate(
        self,
        prompt: str,
        question: SurveyQuestion,
        agent: AgentState,
        retrieved: list[RetrievedEvent],
        use_parametric: bool,
        method: str = "",
    ) -> str:
        return self.generate_batch(
            [prompt],
            questions=[question],
            agent=agent,
            retrieved_lists=[retrieved],
            use_parametric=use_parametric,
            method=method,
        )[0]

    def generate_batch(
        self,
        prompts: list[str],
        questions: list[SurveyQuestion],
        agent: AgentState,
        retrieved_lists: list[list[RetrievedEvent]],
        use_parametric: bool,
        method: str = "",
    ) -> list[str]:
        del questions, retrieved_lists
        adapter = (
            _adapter_name(method, agent.profile.agent_id)
            if use_parametric and method
            else None
        )
        return self._generate_texts(prompts, adapter)

    def _ensure_adapter(self, adapter: str) -> None:
        from peft import LoraConfig, TaskType, get_peft_model

        if not self._peft:
            targets = infer_lora_targets(self.model, self.config.lora_target_modules)
            lora = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=self.config.lora_rank,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=targets,
                bias="none",
            )
            if hasattr(self.model, "enable_input_require_grads"):
                self.model.enable_input_require_grads()
            self.model = get_peft_model(self.model, lora, adapter_name=adapter)
            self._peft = True
            self._adapters.add(adapter)
            return
        if adapter not in self._adapters:
            targets = infer_lora_targets(self.model, self.config.lora_target_modules)
            lora = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=self.config.lora_rank,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=targets,
                bias="none",
            )
            self.model.add_adapter(adapter, lora)
            self._adapters.add(adapter)

    def _fit(self, adapter: str, examples: list[dict[str, str]]) -> None:
        import torch

        self.model.train()
        self.model.set_adapter(adapter)
        trainable = [param for param in self.model.parameters() if param.requires_grad]
        optimizer = torch.optim.AdamW(trainable, lr=self.config.learning_rate)
        batches = _chunk(examples, max(1, self.config.train_batch_size))
        for _ in range(self.config.epochs_per_update):
            for batch in batches:
                optimizer.zero_grad(set_to_none=True)
                loss = self._sft_loss(batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, self.config.max_grad_norm)
                optimizer.step()
        del optimizer
        self.model.eval()

    def _sft_loss(self, batch: list[dict[str, str]]) -> Any:
        import torch

        input_ids: list[list[int]] = []
        labels: list[list[int]] = []
        for example in batch:
            prompt_ids = self._encode(
                [user_message(example["user"])], add_generation_prompt=True
            )
            full_ids = self._encode(
                [
                    user_message(example["user"]),
                    assistant_message(example["assistant"]),
                ],
                add_generation_prompt=False,
            )
            label = list(full_ids)
            prefix = min(len(prompt_ids), len(label))
            label[:prefix] = [-100] * prefix
            input_ids.append(full_ids)
            labels.append(label)
        padded_ids, attn = _pad_left(input_ids, self.tokenizer.pad_token_id)
        padded_labels, _ = _pad_left(labels, -100)
        tensor_ids = torch.tensor(padded_ids, device=self.device)
        tensor_labels = torch.tensor(padded_labels, device=self.device)
        tensor_attn = torch.tensor(attn, device=self.device)
        outputs = self.model(
            input_ids=tensor_ids, attention_mask=tensor_attn, labels=tensor_labels
        )
        return outputs.loss

    def _generate_texts(self, prompts: list[str], adapter: str | None) -> list[str]:
        import torch

        self.model.eval()
        texts = [
            self._apply_chat([user_message(prompt)], add_generation_prompt=True)
            for prompt in prompts
        ]
        encoded = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096,
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        generate_kwargs = {
            **encoded,
            "max_new_tokens": self.config.max_new_tokens,
            "do_sample": False,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        with torch.inference_mode():
            if adapter and self._peft and adapter in self._adapters:
                self.model.set_adapter(adapter)
                outputs = self.model.generate(**generate_kwargs)
            elif self._peft:
                with self.model.disable_adapter():
                    outputs = self.model.generate(**generate_kwargs)
            else:
                outputs = self.model.generate(**generate_kwargs)
        prompt_len = encoded["input_ids"].shape[1]
        decoded = self.tokenizer.batch_decode(
            outputs[:, prompt_len:], skip_special_tokens=True
        )
        return [text.strip() for text in decoded]

    def _apply_chat(
        self, messages: list[dict[str, Any]], add_generation_prompt: bool
    ) -> str:
        kwargs = {
            "tokenize": False,
            "add_generation_prompt": add_generation_prompt,
            "enable_thinking": not self.config.disable_thinking,
        }
        try:
            return self.tokenizer.apply_chat_template(messages, **kwargs)
        except TypeError:
            kwargs.pop("enable_thinking", None)
            return self.tokenizer.apply_chat_template(messages, **kwargs)

    def _encode(
        self, messages: list[dict[str, Any]], add_generation_prompt: bool
    ) -> list[int]:
        text = self._apply_chat(messages, add_generation_prompt=add_generation_prompt)
        return self.tokenizer(text, add_special_tokens=False)["input_ids"]


def _adapter_name(method: str, agent_id: str) -> str:
    return f"{method}__{agent_id}"


def _chunk(items: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _pad_left(
    sequences: list[list[int]], pad_id: int
) -> tuple[list[list[int]], list[list[int]]]:
    width = max(len(seq) for seq in sequences)
    padded: list[list[int]] = []
    attn: list[list[int]] = []
    for seq in sequences:
        gap = width - len(seq)
        padded.append([pad_id] * gap + seq)
        attn.append([0] * gap + [1] * len(seq))
    return padded, attn


def adapter_vector_from_lora(model: Any, adapter: str, dim: int = 128) -> list[float]:
    """Flatten a few LoRA A matrices into a unit vector for the adapter PCA plot."""
    pieces: list[np.ndarray] = []
    for name, param in model.named_parameters():
        if adapter in name and "lora_A" in name:
            pieces.append(param.detach().float().cpu().numpy().ravel())
        if sum(p.size for p in pieces) > 4096:
            break
    if not pieces:
        return [0.0] * dim
    flat = np.concatenate(pieces)
    if flat.size < dim:
        flat = np.pad(flat, (0, dim - flat.size))
    else:
        flat = flat[:dim]
    norm = float(np.linalg.norm(flat))
    if norm:
        flat = flat / norm
    return flat.astype(np.float64).tolist()
