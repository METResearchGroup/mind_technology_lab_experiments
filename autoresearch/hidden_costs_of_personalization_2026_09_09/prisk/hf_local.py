"""Download Qwen3.5-4B from the Hugging Face Hub and serve it locally."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download

DEFAULT_GGUF_REPO = "unsloth/Qwen3.5-4B-GGUF"
DEFAULT_GGUF_FILE = "Qwen3.5-4B-Q4_K_M.gguf"
DEFAULT_MODEL_ID = "Qwen/Qwen3.5-4B"
DEFAULT_PORT = 8088


def llama_server_bin() -> Path:
    env = os.environ.get("LLAMA_SERVER_BIN")
    if env:
        path = Path(env)
        if path.is_file():
            return path
    for candidate in (
        Path("/tmp/llama.cpp/build/bin/llama-server"),
        Path.home() / "llama.cpp" / "build" / "bin" / "llama-server",
    ):
        if candidate.is_file():
            return candidate
    which = shutil.which("llama-server")
    if which:
        return Path(which)
    raise FileNotFoundError(
        "llama-server not found. Build llama.cpp or set LLAMA_SERVER_BIN."
    )


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def wait_healthy(base_url: str, timeout_s: float = 180.0) -> None:
    deadline = time.time() + timeout_s
    urls = (
        base_url.rstrip("/") + "/models",
        (base_url[:-3] if base_url.endswith("/v1") else base_url.rstrip("/"))
        + "/health",
    )
    last_err = "timeout"
    while time.time() < deadline:
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 300:
                        return
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_err = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"llama-server did not become ready: {last_err}")


def download_qwen_gguf(
    repo_id: str = DEFAULT_GGUF_REPO,
    filename: str = DEFAULT_GGUF_FILE,
) -> Path:
    return Path(hf_hub_download(repo_id=repo_id, filename=filename))


def ensure_local_qwen_server(
    port: int = DEFAULT_PORT,
    n_ctx: int = 4096,
    n_threads: int | None = None,
) -> str:
    """Start llama-server on the Hub GGUF if needed.

    Returns an OpenAI-compatible base URL such as ``http://127.0.0.1:8088/v1``.
    """
    base_url = f"http://127.0.0.1:{port}/v1"
    if port_open("127.0.0.1", port):
        wait_healthy(base_url, timeout_s=30)
        return base_url

    gguf = download_qwen_gguf()
    binary = llama_server_bin()
    threads = n_threads or os.cpu_count() or 4
    log_path = Path(os.environ.get("LLAMA_SERVER_LOG", "/tmp/llama-server-qwen.log"))
    log_file = log_path.open("w", encoding="utf-8")
    env = os.environ.copy()
    lib_dir = str(binary.resolve().parent)
    env["LD_LIBRARY_PATH"] = lib_dir + (
        os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
    )
    cmd = [
        str(binary),
        "--model",
        str(gguf),
        "--port",
        str(port),
        "--host",
        "127.0.0.1",
        "--ctx-size",
        str(n_ctx),
        "--threads",
        str(threads),
        "--n-gpu-layers",
        "0",
        "--jinja",
        "--reasoning",
        "off",
    ]
    subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
        cwd=lib_dir,
    )
    wait_healthy(base_url, timeout_s=180)
    return base_url
