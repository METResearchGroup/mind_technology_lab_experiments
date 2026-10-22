"""Hit the demo API and check the public contract.

This script does not read or print secrets. A write without a token must be rejected.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def _request(
    url: str,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    # workers.dev returns 1010 for clients that send no User-Agent.
    request_headers = {"user-agent": "cloudflare-deploy-demo-smoke/1.0"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url, data=body, method=method, headers=request_headers
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            return response.status, raw_headers, response.read()
    except urllib.error.HTTPError as exc:
        raw_headers = {key.lower(): value for key, value in exc.headers.items()}
        return exc.code, raw_headers, exc.read()


def _json_body(raw: bytes) -> object:
    return json.loads(raw.decode())


def main() -> int:
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8787"
    origin = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:3001"
    failures: list[str] = []

    status, _, raw = _request(f"{base}/health")
    health = _json_body(raw)
    if status != 200 or not isinstance(health, dict) or health.get("status") != "ok":
        failures.append(f"health returned {status}: {raw.decode()[:200]}")
    elif health.get("storage") != "d1":
        failures.append("health did not report d1 storage")
    elif "secret_configured" not in health:
        failures.append("health did not report secret_configured")

    status, _, raw = _request(f"{base}/api/notes")
    notes = _json_body(raw)
    if (
        status != 200
        or not isinstance(notes, dict)
        or not isinstance(notes.get("notes"), list)
    ):
        failures.append(f"notes returned {status}: {raw.decode()[:200]}")

    status, _, raw = _request(
        f"{base}/api/notes",
        method="POST",
        body=b'{"body":"smoke"}',
        headers={"content-type": "application/json"},
    )
    if status != 401:
        failures.append(f"unauthenticated write returned {status}, expected 401")

    status, headers, _ = _request(
        f"{base}/api/notes",
        method="OPTIONS",
        headers={
            "origin": origin,
            "access-control-request-method": "GET",
            "access-control-request-headers": "content-type",
        },
    )
    allow_origin = headers.get("access-control-allow-origin")
    if status != 204 or allow_origin != origin:
        failures.append(
            f"CORS preflight returned {status} allow-origin={allow_origin!r}"
        )

    blocked_origin = "https://example.invalid"
    _, blocked_headers, _ = _request(
        f"{base}/api/notes",
        method="OPTIONS",
        headers={"origin": blocked_origin, "access-control-request-method": "GET"},
    )
    if blocked_headers.get("access-control-allow-origin") == blocked_origin:
        failures.append("CORS allowed an origin that is not configured")

    if failures:
        for failure in failures:
            print(failure)
        return 1

    secret_configured = (
        health.get("secret_configured") if isinstance(health, dict) else None
    )
    note_count = len(notes["notes"]) if isinstance(notes, dict) else 0
    print(
        json.dumps(
            {
                "ok": True,
                "base": base,
                "secret_configured": secret_configured,
                "note_count": note_count,
                "cors_origin": origin,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
