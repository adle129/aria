#!/usr/bin/env python3
"""R1 Wave 6 E2E smoke test against a running ARIA stack.

Exercises: health preflight → (optional login) → RFQ upload → dimension_review
→ confirm-dimensions → completed matrix.

Usage (production / docker-compose.prod):
  python scripts/r1_e2e_smoke.py --base-url http://localhost/api/v1 \\
    --username engineer --password secret \\
    --rfq samples/rfq/mock_chassis_rfq.docx

Health-only:
  python scripts/r1_e2e_smoke.py --base-url http://localhost/api/v1 --health-only
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SmokeError(RuntimeError):
    pass


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, Any]:
    req_headers = dict(headers or {})
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    if body is not None and "Content-Type" not in req_headers:
        req_headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"msg": raw}
        return exc.code, payload


def _multipart_upload(url: str, field_name: str, file_path: Path, token: str | None) -> tuple[int, Any]:
    boundary = f"----aria-smoke-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=180.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"msg": raw}


def step_health(base: str, *, allow_warnings: bool) -> dict[str, Any]:
    status, body = _request("GET", f"{base}/health")
    if status != 200 or not isinstance(body, dict):
        raise SmokeError(f"health failed: HTTP {status} {body}")
    print(f"[ok] health profile={body.get('aria_ui_profile')} mock_llm={body.get('mock_llm')} mock_rag={body.get('mock_rag')}")
    warnings = body.get("production_warnings") or []
    if warnings:
        for w in warnings:
            print(f"[warn] {w}")
        if not allow_warnings:
            raise SmokeError("production_warnings non-empty (use --allow-warnings to bypass)")
    return body


def step_login(base: str, username: str, password: str) -> str:
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    status, body = _request("POST", f"{base}/auth/login", body=payload)
    if status != 200 or body.get("code") != 200:
        raise SmokeError(f"login failed: HTTP {status} {body}")
    token = body["data"]["access_token"]
    print(f"[ok] login as {body['data']['user']['username']} ({body['data']['user']['role']})")
    return token


def step_knowledge_stats(base: str, token: str | None, *, min_chunks: int) -> None:
    status, body = _request("GET", f"{base}/knowledge/stats", token=token)
    if status != 200:
        print(f"[warn] knowledge/stats HTTP {status} — skip chunk check")
        return
    data = body.get("data") if isinstance(body, dict) else body
    chunks = int((data or {}).get("total_chunks") or 0)
    print(f"[ok] knowledge chunks={chunks} projects={(data or {}).get('total_projects')}")
    if chunks < min_chunks:
        print(f"[warn] indexed chunks {chunks} < {min_chunks} — Top-3 may be empty / insufficient_evidence")


def step_upload_rfq(base: str, token: str | None, rfq_path: Path) -> str:
    status, body = _multipart_upload(f"{base}/rfq/upload", "file", rfq_path, token)
    if status != 200 or body.get("code") != 200:
        raise SmokeError(f"upload failed: HTTP {status} {body}")
    task_id = body["data"]["task_id"]
    print(f"[ok] upload task_id={task_id}")
    return task_id


def step_wait_status(
    base: str,
    token: str | None,
    task_id: str,
    target: str,
    *,
    timeout: float,
    poll: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, body = _request("GET", f"{base}/rfq/tasks/{task_id}/status", token=token)
        if status != 200:
            raise SmokeError(f"status poll failed: HTTP {status} {body}")
        state = body.get("status")
        progress = body.get("progress")
        message = body.get("message")
        print(f"  … status={state} progress={progress}% {message or ''}")
        if state == target:
            return body
        if state == "failed":
            raise SmokeError(f"task failed: {message}")
        time.sleep(poll)
    raise SmokeError(f"timeout waiting for status={target}")


def step_confirm_dimensions(base: str, token: str | None, task_id: str) -> None:
    status, body = _request("GET", f"{base}/rfq/tasks/{task_id}", token=token)
    if status != 200 or body.get("code") != 200:
        raise SmokeError(f"get task failed: HTTP {status} {body}")
    task = body["data"]
    draft = task.get("dimension_draft") or {}
    items = list(draft.get("items") or [])
    if not any(i.get("in_scope") for i in items):
        if not items:
            raise SmokeError("dimension_draft has no items")
        items = [{**items[0], "in_scope": True}]
    payload = json.dumps(
        {
            "baseline_version": draft.get("baseline_version"),
            "items": items,
            "custom_items": draft.get("custom_items") or [],
        }
    ).encode("utf-8")
    status, body = _request("POST", f"{base}/rfq/tasks/{task_id}/confirm-dimensions", token=token, body=payload)
    if status != 200 or body.get("code") != 200:
        raise SmokeError(f"confirm-dimensions failed: HTTP {status} {body}")
    print("[ok] confirm-dimensions")


def step_verify_completed(base: str, token: str | None, task_id: str) -> None:
    status, body = _request("GET", f"{base}/rfq/tasks/{task_id}", token=token)
    if status != 200 or body.get("code") != 200:
        raise SmokeError(f"get task failed: HTTP {status} {body}")
    task = body["data"]
    if task.get("processing_status") != "completed":
        raise SmokeError(f"expected completed, got {task.get('processing_status')}")
    table = task.get("comparison_table") or {}
    rows = table.get("matrix_rows") or []
    dims = table.get("comparison_dimensions") or []
    in_scope_names = {
        str(i.get("name"))
        for i in (task.get("dimension_draft") or {}).get("items") or []
        if i.get("in_scope") is True
    }
    if not rows:
        raise SmokeError("comparison_table.matrix_rows empty")
    if in_scope_names and not dims:
        raise SmokeError("comparison_dimensions empty despite in_scope items")
    if table.get("insufficient_evidence"):
        print("[warn] insufficient_evidence=true — index more engagements or lower RAG_SIMILARITY_THRESHOLD")
    print(
        f"[ok] completed matrix_rows={len(rows)} top3={len(task.get('similar_projects') or [])} "
        f"confidence={table.get('overall_confidence')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="R1 E2E smoke test")
    parser.add_argument("--base-url", default="http://localhost/api/v1")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--rfq", type=Path, default=Path("samples/rfq/mock_chassis_rfq.docx"))
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--min-chunks", type=int, default=1)
    parser.add_argument("--parse-timeout", type=float, default=600.0)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    try:
        health = step_health(base, allow_warnings=args.allow_warnings)
        if args.health_only:
            print("[done] health-only")
            return 0

        token: str | None = None
        if health.get("auth_enabled"):
            if not args.username or not args.password:
                raise SmokeError("auth_enabled — provide --username and --password")
            token = step_login(base, args.username, args.password)

        if not args.rfq.is_file():
            raise SmokeError(f"RFQ file not found: {args.rfq}")

        step_knowledge_stats(base, token, min_chunks=args.min_chunks)
        task_id = step_upload_rfq(base, token, args.rfq)
        step_wait_status(
            base,
            token,
            task_id,
            "dimension_review",
            timeout=args.parse_timeout,
            poll=args.poll_interval,
        )
        step_confirm_dimensions(base, token, task_id)
        step_verify_completed(base, token, task_id)
    except (SmokeError, URLError) as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1

    print("[done] R1 E2E smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
