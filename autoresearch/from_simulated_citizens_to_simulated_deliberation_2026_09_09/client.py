"""Hugging Face Inference client for Qwen3.5-4B."""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_MODEL = "Qwen/Qwen3.5-4B"
DEFAULT_PROVIDER = "featherless-ai"


@dataclass(frozen=True)
class ChatResult:
    text: str
    raw: str
    prompt_tokens: int
    completion_tokens: int
    elapsed_sec: float


class ChatClient(Protocol):
    def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> ChatResult: ...


class QwenClient:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        provider: str = DEFAULT_PROVIDER,
        token: str | None = None,
        timeout: int = 120,
    ) -> None:
        resolved = token or os.environ.get("HF_TOKEN")
        if not resolved:
            raise RuntimeError("HF_TOKEN is not set")
        from huggingface_hub import InferenceClient

        self.model = model
        self.client = InferenceClient(
            model=model,
            token=resolved,
            provider=provider,
            timeout=timeout,
        )

    def chat(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> ChatResult:
        extra_body: dict[str, Any] = {
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if seed is not None:
            extra_body["seed"] = seed
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(6):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=list(messages),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_body=extra_body,
                )
                message = response.choices[0].message
                text = (message.content or "").strip()
                usage = response.usage
                return ChatResult(
                    text=text,
                    raw=text,
                    prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    elapsed_sec=time.monotonic() - started,
                )
            except Exception as error:
                last_error = error
                sleep_for = min(2**attempt, 20) + random.random()
                time.sleep(sleep_for)
        raise RuntimeError(f"Qwen chat failed after retries: {last_error}")


def map_parallel[T, R](
    items: Sequence[T],
    worker: Callable[[T], R],
    *,
    workers: int,
) -> list[R]:
    if not items:
        return []
    if workers <= 1:
        return [worker(item) for item in items]
    by_index: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(worker, item): index for index, item in enumerate(items)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            by_index[index] = future.result()
    return [by_index[index] for index in range(len(items))]
