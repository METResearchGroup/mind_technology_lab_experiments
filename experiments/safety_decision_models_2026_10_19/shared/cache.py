"""SQLite response cache and Hugging Face revision pinning.

Run from the experiment folder:

    uv run python -c "from shared.cache import ResponseCache; print(ResponseCache.__name__)"
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi
from pydantic import BaseModel

from shared.records import PredictionRecord

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_DB = EXPERIMENT_ROOT / "cache" / "responses.db"
REVISION_MANIFEST = EXPERIMENT_ROOT / "outputs" / "manifests" / "dataset_revisions.json"
CHARS_PER_TOKEN_ESTIMATE = 4


class RevisionMismatchError(RuntimeError):
    """Raised when a dataset load uses a different commit than the pin."""


class ResponseCache:
    """Store provider responses keyed by arm, model, template, and example."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DEFAULT_CACHE_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def cache_key(
        arm: str,
        model_version: str,
        template_version: str,
        example_id: str,
    ) -> str:
        """Hash arm, model version, template version, and example id."""
        raw = "|".join([arm, model_version, template_version, example_id])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> PredictionRecord | None:
        """Return a cached prediction or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM responses WHERE cache_key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        return PredictionRecord.model_validate_json(row["payload"])

    def put(self, key: str, record: PredictionRecord) -> None:
        """Persist a prediction row."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO responses (cache_key, payload) VALUES (?, ?)",
                (key, record.model_dump_json()),
            )


def estimate_token_count(text: str) -> int:
    """Rough token count for Clef truncation checks."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def _experiment_root_on_path() -> Path:
    return EXPERIMENT_ROOT.resolve()


def _sys_path_without_experiment_root() -> list[str]:
    root = _experiment_root_on_path()
    filtered: list[str] = []
    for entry in sys.path:
        try:
            resolved = Path(entry).resolve() if entry else Path.cwd().resolve()
        except OSError:
            filtered.append(entry)
            continue
        if resolved == root:
            continue
        filtered.append(entry)
    return filtered


def _local_datasets_root() -> Path:
    return (EXPERIMENT_ROOT / "datasets").resolve()


def _is_local_datasets_module(module_name: str) -> bool:
    """True for experiment loader modules under ``datasets/``, not Hugging Face."""
    module = sys.modules.get(module_name)
    if module is None:
        return False
    local_root = _local_datasets_root()
    file_path = getattr(module, "__file__", None)
    if file_path:
        try:
            resolved = Path(file_path).resolve()
        except OSError:
            return False
        if resolved == local_root / "__init__.py" or local_root in resolved.parents:
            return True
    if module_name == "datasets":
        for entry in getattr(module, "__path__", []) or []:
            try:
                if Path(entry).resolve() == local_root:
                    return True
            except OSError:
                continue
    return False


@contextmanager
def _isolated_hf_datasets_import() -> Iterator[None]:
    """Hide local ``datasets/`` loaders while Hugging Face datasets runs."""
    saved_local: dict[str, Any] = {}
    for name in list(sys.modules):
        if name == "datasets" or name.startswith("datasets."):
            if _is_local_datasets_module(name):
                saved_local[name] = sys.modules.pop(name)
    old_path = sys.path[:]
    sys.path = _sys_path_without_experiment_root()
    try:
        yield
    finally:
        sys.path = old_path
        for name, module in saved_local.items():
            sys.modules[name] = module


def _import_hf_datasets() -> Any:
    """Import the Hugging Face ``datasets`` package, not this repo's loaders."""
    cached = sys.modules.get("_hf_datasets_package")
    if cached is not None and hasattr(cached, "load_dataset"):
        hf = cached
    else:
        import importlib

        hf = importlib.import_module("datasets")
        sys.modules["_hf_datasets_package"] = hf
    # ``load_dataset`` and friends do ``import datasets`` internally; bind the HF
    # package while local ``datasets/`` loaders are off sys.path.
    sys.modules["datasets"] = hf
    return hf


def load_hf_dataset(
    repo_id: str,
    *,
    name: str | None = None,
    split: str,
    token: str | None = None,
    revision: str | None = None,
) -> Any:
    """Load a Hugging Face split with revision pinning."""
    dataset_key = _dataset_manifest_key(repo_id, name)
    pinned = _read_pinned_revision(dataset_key)
    if pinned and revision and revision != pinned:
        raise RevisionMismatchError(
            f"Refusing {repo_id}: requested revision {revision} != pin {pinned}"
        )
    use_revision = revision or pinned
    kwargs: dict[str, Any] = {"path": repo_id, "split": split, "token": token}
    if name is not None:
        kwargs["name"] = name
    if use_revision:
        kwargs["revision"] = use_revision
    with _isolated_hf_datasets_import():
        hf = _import_hf_datasets()
        table = hf.load_dataset(**kwargs)
    commit = _resolve_dataset_commit(repo_id, use_revision, token)
    if pinned is None:
        _write_pinned_revision(dataset_key, commit)
    elif commit != pinned:
        raise RevisionMismatchError(
            f"Refusing {repo_id}: hub commit {commit} != pin {pinned}"
        )
    return table


def list_hf_splits(
    repo_id: str,
    *,
    name: str | None = None,
    token: str | None = None,
    revision: str | None = None,
) -> list[str]:
    """Return split names for a Hugging Face dataset (revision-aware)."""
    dataset_key = _dataset_manifest_key(repo_id, name)
    pinned = _read_pinned_revision(dataset_key)
    if pinned and revision and revision != pinned:
        raise RevisionMismatchError(
            f"Refusing {repo_id}: requested revision {revision} != pin {pinned}"
        )
    use_revision = revision or pinned
    builder_kwargs: dict[str, Any] = {"path": repo_id, "token": token}
    if name is not None:
        builder_kwargs["name"] = name
    if use_revision:
        builder_kwargs["revision"] = use_revision
    with _isolated_hf_datasets_import():
        hf = _import_hf_datasets()
        builder = hf.load_dataset_builder(**builder_kwargs)
    splits = list(builder.info.splits.keys())
    return sorted(splits)


def _dataset_manifest_key(repo_id: str, config: str | None) -> str:
    if config:
        return f"{repo_id}::{config}"
    return repo_id


def _read_pinned_revision(dataset_key: str) -> str | None:
    if not REVISION_MANIFEST.is_file():
        return None
    payload = json.loads(REVISION_MANIFEST.read_text(encoding="utf-8"))
    entry = payload.get(dataset_key)
    if not entry:
        return None
    return str(entry.get("revision", "")) or None


def _write_pinned_revision(dataset_key: str, revision: str) -> None:
    REVISION_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if REVISION_MANIFEST.is_file():
        payload = json.loads(REVISION_MANIFEST.read_text(encoding="utf-8"))
    payload[dataset_key] = {"revision": revision}
    REVISION_MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _resolve_dataset_commit(
    repo_id: str, revision: str | None, token: str | None
) -> str:
    api = HfApi(token=token)
    info = api.repo_info(repo_id=repo_id, repo_type="dataset", revision=revision)
    return info.sha


class DatasetRevisionPin(BaseModel):
    """Pinned commit for one Hugging Face dataset."""

    revision: str


def iter_table_rows(table: Any) -> Iterator[dict[str, Any]]:
    """Yield row dicts from a Hugging Face Dataset."""
    for index in range(len(table)):
        row = table[index]
        if isinstance(row, dict):
            yield row
        else:
            yield dict(row)
