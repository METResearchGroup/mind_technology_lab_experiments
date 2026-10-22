"""FastAPI application for the Cloudflare Python Workers demo."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from workers import asgi

logger = logging.getLogger("cloudflare_deploy_demo")

app = FastAPI(title="Cloudflare deploy demo")
Default = asgi.entrypoint(app)

_LOCAL_ORIGINS = (
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8788",
    "http://127.0.0.1:8788",
)
_MAX_BODY_LENGTH = 200


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=_MAX_BODY_LENGTH)


def _worker_env(request: Request) -> object:
    env = request.scope.get("env")
    if env is None:
        raise HTTPException(status_code=500, detail="Worker bindings are unavailable")
    return env


def _binding(env: object, name: str) -> object | None:
    value = getattr(env, name, None)
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text == "None":
        return None
    return value


def _allowed_origins(env: object) -> set[str]:
    raw = _binding(env, "CORS_ORIGINS")
    extra: set[str] = set()
    if raw is not None:
        extra = {part.strip() for part in str(raw).split(",") if part.strip()}
    return set(_LOCAL_ORIGINS) | extra


def _tokens_match(presented: str, expected: str) -> bool:
    presented_hash = hashlib.sha256(presented.encode()).digest()
    expected_hash = hashlib.sha256(expected.encode()).digest()
    return hmac.compare_digest(presented_hash, expected_hash)


def _to_python(value: object) -> object:
    converter = getattr(value, "to_py", None)
    if callable(converter):
        return converter()
    return value


def _rows(result: object) -> list[dict[str, object]]:
    raw_rows = _to_python(getattr(result, "results", []))
    if not isinstance(raw_rows, list):
        return []
    notes: list[dict[str, object]] = []
    for row in raw_rows:
        converted = _to_python(row)
        if isinstance(converted, dict):
            notes.append({str(key): item for key, item in converted.items()})
    return notes


def _log(level: int, message: str, **fields: object) -> None:
    logger.log(level, json.dumps({"message": message, **fields}))


@app.middleware("http")
async def add_cors(request: Request, call_next):  # noqa: ANN001
    env = request.scope.get("env")
    origin = request.headers.get("origin")
    allowed = _allowed_origins(env) if env is not None else set(_LOCAL_ORIGINS)
    if request.method == "OPTIONS":
        response: Response = Response(status_code=204)
    else:
        response = await call_next(request)
    if origin and origin in allowed:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Vary"] = "Origin"
    return response


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    env = _worker_env(request)
    _log(logging.INFO, "health")
    return {
        "status": "ok",
        "storage": "d1",
        "secret_configured": _binding(env, "NOTE_TOKEN") is not None,
    }


@app.get("/api/notes")
async def list_notes(request: Request) -> dict[str, object]:
    env = _worker_env(request)
    try:
        result = await env.DB.prepare(
            "SELECT id, body, created_at FROM notes ORDER BY id DESC LIMIT 20"
        ).all()
    except Exception as exc:
        _log(logging.ERROR, "list notes failed", error=str(exc))
        raise HTTPException(status_code=503, detail="database query failed") from exc
    return {"notes": _rows(result)}


def _require_note_token(env: object, authorization: str | None) -> None:
    expected = _binding(env, "NOTE_TOKEN")
    if expected is None:
        raise HTTPException(status_code=503, detail="NOTE_TOKEN is not configured")
    presented = ""
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    if not _tokens_match(presented, str(expected)):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/api/notes", status_code=201)
async def create_note(
    payload: NoteIn,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    env = _worker_env(request)
    _require_note_token(env, authorization)
    try:
        result = await (
            env.DB.prepare(
                "INSERT INTO notes (body) VALUES (?) RETURNING id, body, created_at"
            )
            .bind(payload.body)
            .all()
        )
    except Exception as exc:
        _log(logging.ERROR, "create note failed", error=str(exc))
        raise HTTPException(status_code=503, detail="database query failed") from exc
    rows = _rows(result)
    if not rows:
        raise HTTPException(status_code=503, detail="database query failed")
    _log(logging.INFO, "note created", id=rows[0].get("id"))
    return {"note": rows[0]}
