#!/usr/bin/env python3
"""WhatsApp-triggered runner service for quote smoke tests."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, Response


APP_TITLE = "Quote Smoke WhatsApp Trigger"
RUNS_DIR = Path(os.getenv("RUNS_DIR", "runs"))
BOT_PATH = Path(os.getenv("QUOTE_BOT_PATH", "quote_smoke_bot.py"))
MAX_RUNS = int(os.getenv("MAX_RUNS", "100"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "10"))
MAX_ACTIVE_JOBS = int(os.getenv("MAX_ACTIVE_JOBS", "1"))
ALLOWED_SENDERS = {
    sender.strip() for sender in os.getenv("WHATSAPP_ALLOWED_SENDERS", "").split(",") if sender.strip()
}
SERVICE_TOKEN = os.getenv("WEBHOOK_SERVICE_TOKEN", "")

RUNS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RunRecord:
    run_id: str
    status: str
    started_at: str
    finished_at: str = ""
    exit_code: int | None = None
    runs: int = 1
    concurrency: int = 1
    log_path: str = ""
    error: str = ""


RUNS: dict[str, RunRecord] = {}
RUNS_LOCK = threading.Lock()

app = FastAPI(title=APP_TITLE)


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def twiml_message(text: str) -> Response:
    safe = escape(text)
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe}</Message></Response>'
    return Response(content=body, media_type="application/xml")


def parse_command(body: str) -> tuple[str, list[str]]:
    parts = [p for p in body.strip().split() if p]
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def count_active_jobs() -> int:
    with RUNS_LOCK:
        return sum(1 for record in RUNS.values() if record.status == "running")


def build_bot_command(runs: int, concurrency: int) -> list[str]:
    return [
        sys.executable,
        "-u",
        str(BOT_PATH),
        "--runs",
        str(runs),
        "--concurrency",
        str(concurrency),
        "--progress-every",
        "1",
        "--run-retries",
        "0",
        "--checkpoint-grace-ms",
        "10000",
        "--ready-timeout-ms",
        "30000",
    ]


def execute_job(run_id: str, runs: int, concurrency: int) -> None:
    log_path = RUNS_DIR / f"{run_id}.log"
    cmd = build_bot_command(runs=runs, concurrency=concurrency)

    with RUNS_LOCK:
        RUNS[run_id].log_path = str(log_path)

    try:
        with log_path.open("w", encoding="utf-8") as fp:
            fp.write(f"Started at: {utc_now()}\n")
            fp.write(f"Command: {' '.join(cmd)}\n\n")
            fp.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=str(Path.cwd()),
                stdout=fp,
                stderr=subprocess.STDOUT,
                text=True,
            )
            exit_code = proc.wait()
            fp.write(f"\nFinished at: {utc_now()}\nExit code: {exit_code}\n")
            fp.flush()

        with RUNS_LOCK:
            RUNS[run_id].status = "success" if exit_code == 0 else "failed"
            RUNS[run_id].exit_code = exit_code
            RUNS[run_id].finished_at = utc_now()
    except Exception as exc:  # noqa: BLE001
        with RUNS_LOCK:
            RUNS[run_id].status = "failed"
            RUNS[run_id].error = str(exc)
            RUNS[run_id].finished_at = utc_now()


def start_job(runs: int, concurrency: int) -> RunRecord:
    run_id = uuid.uuid4().hex[:10]
    record = RunRecord(
        run_id=run_id,
        status="running",
        started_at=utc_now(),
        runs=runs,
        concurrency=concurrency,
    )
    with RUNS_LOCK:
        RUNS[run_id] = record

    thread = threading.Thread(
        target=execute_job,
        args=(run_id, runs, concurrency),
        daemon=True,
        name=f"smoke-{run_id}",
    )
    thread.start()
    return record


def format_help() -> str:
    return (
        "Commands:\n"
        "- smoke [runs] [concurrency] (example: smoke 10 2)\n"
        "- status <run_id>\n"
        "- latest\n"
        "- help"
    )


def find_latest_record() -> RunRecord | None:
    with RUNS_LOCK:
        if not RUNS:
            return None
        return sorted(RUNS.values(), key=lambda r: r.started_at, reverse=True)[0]


def get_record(run_id: str) -> RunRecord | None:
    with RUNS_LOCK:
        return RUNS.get(run_id)


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def validate_sender(sender: str) -> bool:
    if not ALLOWED_SENDERS:
        return True
    return sender in ALLOWED_SENDERS


def validate_service_token(request: Request) -> bool:
    if not SERVICE_TOKEN:
        return True
    return request.headers.get("x-service-token", "") == SERVICE_TOKEN


def handle_command(body: str) -> str:
    cmd, args = parse_command(body)
    if cmd in {"", "help"}:
        return format_help()

    if cmd == "latest":
        record = find_latest_record()
        if not record:
            return "No runs yet."
        return (
            f"Run {record.run_id}: {record.status}\n"
            f"runs={record.runs} concurrency={record.concurrency}\n"
            f"log={record.log_path}"
        )

    if cmd == "status":
        if not args:
            return "Usage: status <run_id>"
        record = get_record(args[0])
        if not record:
            return f"Run {args[0]} not found."
        return (
            f"Run {record.run_id}: {record.status}\n"
            f"started={record.started_at}\n"
            f"finished={record.finished_at or '-'}\n"
            f"exit_code={record.exit_code if record.exit_code is not None else '-'}\n"
            f"log={record.log_path or '-'}\n"
            f"error={record.error or '-'}"
        )

    if cmd == "smoke":
        runs = parse_int(args[0], 1) if len(args) >= 1 else 1
        concurrency = parse_int(args[1], 1) if len(args) >= 2 else 1
        if runs < 1:
            return "runs must be >= 1"
        if concurrency < 1:
            return "concurrency must be >= 1"
        if runs > MAX_RUNS:
            return f"runs too high (max {MAX_RUNS})"
        if concurrency > MAX_CONCURRENCY:
            return f"concurrency too high (max {MAX_CONCURRENCY})"
        if count_active_jobs() >= MAX_ACTIVE_JOBS:
            return "Another job is already running. Try again shortly."

        record = start_job(runs=runs, concurrency=concurrency)
        return (
            f"Started run {record.run_id}\n"
            f"runs={runs} concurrency={concurrency}\n"
            f"Use: status {record.run_id}"
        )

    return "Unknown command. Send 'help' for options."


@app.get("/healthz")
def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
) -> Response:
    if not validate_service_token(request):
        return twiml_message("Unauthorized")
    if not validate_sender(From):
        return twiml_message("Sender not allowed")

    result = handle_command(Body)
    return twiml_message(result)


@app.post("/webhook/whatsapp/json")
async def whatsapp_webhook_json(request: Request) -> Response:
    if not validate_service_token(request):
        return twiml_message("Unauthorized")
    payload: dict[str, Any] = await request.json()
    sender = str(payload.get("from", ""))
    body = str(payload.get("message", ""))
    if not validate_sender(sender):
        return twiml_message("Sender not allowed")

    result = handle_command(body)
    return twiml_message(result)
