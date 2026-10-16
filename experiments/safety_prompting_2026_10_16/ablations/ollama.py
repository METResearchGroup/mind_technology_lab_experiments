# ruff: noqa: E501
"""Local Ollama chat calls for gemma3:1b.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.ablations.ollama import MODEL_NAME; print(MODEL_NAME)"
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

MODEL_NAME = "gemma3:1b"
TEMPERATURE = 0
NUM_PREDICT = 256
NUM_CTX = 8192
KEEP_ALIVE = "30m"
CHAT_URL = "http://127.0.0.1:11434/api/chat"
REQUEST_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class Generation:
    """One model completion."""

    text: str
    latency_ms: float
    eval_count: int | None
    done_reason: str


def generate(model: str, system_prompt: str, user_prompt: str) -> Generation:
    """Send one chat request to the local Ollama server.

    Parameters
    ----------
    model
        Ollama model name, for example ``gemma3:1b``.
    system_prompt
        System message for this ablation. An empty string omits the system
        message, which is the control condition.
    user_prompt
        User message, which is one dataset example.

    Returns
    -------
    Generation
        Response text, latency, token count, and stop reason.
    """
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    payload = {
        "model": model,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "messages": messages,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": NUM_PREDICT,
            "num_ctx": NUM_CTX,
            "seed": 0,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.perf_counter()
        request = urllib.request.Request(
            CHAT_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                raw = response.read()
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(attempt)
            continue
        latency_ms = (time.perf_counter() - started) * 1000
        parsed = json.loads(raw)
        message = parsed.get("message") or {}
        text = message.get("content")
        if not isinstance(text, str):
            text = ""
        eval_count = parsed.get("eval_count")
        if eval_count is not None:
            eval_count = int(eval_count)
        done_reason = str(parsed.get("done_reason") or "")
        return Generation(
            text=text,
            latency_ms=latency_ms,
            eval_count=eval_count,
            done_reason=done_reason,
        )
    raise SystemExit(
        "Ollama did not answer at "
        f"{CHAT_URL}. Start Ollama and pull {MODEL_NAME}. Last error: {last_error}"
    )
