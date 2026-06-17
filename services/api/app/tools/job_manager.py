from __future__ import annotations

import json
import threading
import time
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable

from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.file_tools import ensure_dir, write_json, write_text
from app.tools.run_history import utc_now

JOBS_DIR = "jobs"
JOBS_JSONL = "jobs/jobs.jsonl"
LATEST_JOB_JSON = "jobs/latest_job.json"
EVENT_STREAM_POLL_SECONDS = 0.25
ACTIVE_JOB_IDS: set[str] = set()
ACTIVE_JOB_LOCK = threading.Lock()


class JobCancelled(RuntimeError):
    pass


def _job_id(job_type: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in job_type.lower()).strip("_") or "job"
    stamp = utc_now().replace(":", "").replace("-", "").replace(".", "").replace("+", "z")
    return f"job_{cleaned}_{stamp}"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            safe[key] = "[redacted]"
        else:
            safe[key] = value
    return safe


def _job_path(project_dir: Path, job_id: str) -> Path:
    return project_dir / JOBS_DIR / f"{job_id}.json"


def _log_path(project_dir: Path, job_id: str) -> Path:
    return project_dir / JOBS_DIR / f"{job_id}.log"


def _cancel_path(project_dir: Path, job_id: str) -> Path:
    return project_dir / JOBS_DIR / f"{job_id}.cancel.json"


def _events_path(project_dir: Path, job_id: str) -> Path:
    return project_dir / JOBS_DIR / f"{job_id}.events.jsonl"


def _relative(path: Path, project_dir: Path) -> str:
    return path.relative_to(project_dir).as_posix()


def _is_cancel_requested(project_dir: Path, job_id: str) -> bool:
    return _cancel_path(project_dir, job_id).exists()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _event_sequence(project_dir: Path, job_id: str) -> int:
    events_path = _events_path(project_dir, job_id)
    if not events_path.exists():
        return 1
    try:
        return sum(1 for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()) + 1
    except OSError:
        return 1


def _append_job_event(
    project_dir: Path,
    record: dict[str, Any],
    event_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job_id = str(record["job_id"])
    event = {
        "schema_version": "researchagent.job.event.v3",
        "sequence": _event_sequence(project_dir, job_id),
        "project_id": record["project_id"],
        "job_id": job_id,
        "job_type": record["job_type"],
        "event_type": event_type,
        "status": record.get("status"),
        "progress": record.get("progress"),
        "current_step": record.get("current_step"),
        "message": message,
        "created_at": utc_now(),
        "cancel_requested": bool(record.get("cancel_requested")),
    }
    if details:
        event["details"] = details
    _append_jsonl(_events_path(project_dir, job_id), event)
    return event


def read_project_job_events(
    project_id: str,
    job_id: str,
    *,
    since_sequence: int = 0,
    limit: int = 200,
) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    if not _job_path(project_dir, job_id).exists():
        raise FileNotFoundError(f"job not found: {job_id}")
    events = [
        event
        for event in _read_jsonl(_events_path(project_dir, job_id))
        if int(event.get("sequence") or 0) > max(0, since_sequence)
    ]
    events = events[: max(1, min(limit, 1000))]
    latest_sequence = 0
    all_events = _read_jsonl(_events_path(project_dir, job_id))
    if all_events:
        latest_sequence = max(int(item.get("sequence") or 0) for item in all_events)
    return {
        "schema_version": "researchagent.job.events.v1",
        "project_id": project_id,
        "job_id": job_id,
        "events_file": _relative(_events_path(project_dir, job_id), project_dir),
        "events": events,
        "latest_sequence": latest_sequence,
        "returned": len(events),
    }


def stream_project_job_events(
    project_id: str,
    job_id: str,
    *,
    since_sequence: int = 0,
    max_events: int = 200,
    idle_heartbeat_seconds: float = 5.0,
) -> Iterator[str]:
    """Yield Server-Sent Events for a local job event timeline.

    The stream is intentionally finite for the local MVP: it exits after the job
    reaches a terminal state and all observed events have been emitted. Clients
    can reconnect with since_sequence for polling-like behavior.
    """
    project_service.require_project(project_id)
    emitted = 0
    last_sequence = max(0, since_sequence)
    last_heartbeat = time.time()
    while emitted < max(1, min(max_events, 2000)):
        payload = read_project_job_events(project_id, job_id, since_sequence=last_sequence, limit=100)
        events = payload.get("events") if isinstance(payload, dict) else []
        if isinstance(events, list) and events:
            for event in events:
                sequence = int(event.get("sequence") or last_sequence)
                last_sequence = max(last_sequence, sequence)
                emitted += 1
                yield f"id: {sequence}\nevent: {event.get('event_type', 'message')}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            last_heartbeat = time.time()
        record = read_project_job(project_id, job_id)
        if record.get("status") in {"completed", "failed", "cancelled"} and last_sequence >= int(payload.get("latest_sequence") or 0):
            break
        if time.time() - last_heartbeat >= idle_heartbeat_seconds:
            heartbeat = {
                "schema_version": "researchagent.job.heartbeat.v1",
                "project_id": project_id,
                "job_id": job_id,
                "status": record.get("status"),
                "progress": record.get("progress"),
                "current_step": record.get("current_step"),
                "created_at": utc_now(),
            }
            yield f"event: heartbeat\ndata: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
            last_heartbeat = time.time()
        time.sleep(EVENT_STREAM_POLL_SECONDS)


def list_project_jobs(project_id: str, limit: int = 50) -> list[dict[str, Any]]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    records = _read_jsonl(project_dir / JOBS_JSONL)
    # Return the most recent event for each job so the UI does not show duplicate start/end records.
    by_job: dict[str, dict[str, Any]] = {}
    for record in records:
        job_id = record.get("job_id")
        if isinstance(job_id, str):
            by_job[job_id] = record
    return list(reversed(list(by_job.values())))[: max(1, min(limit, 200))]


def read_project_job(project_id: str, job_id: str) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    path = _job_path(project_dir, job_id)
    if not path.exists():
        raise FileNotFoundError(f"job not found: {job_id}")
    last_error: json.JSONDecodeError | None = None
    for _attempt in range(5):
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = exc
        time.sleep(0.02)
    if last_error is not None:
        raise last_error
    raise FileNotFoundError(f"job file is temporarily empty: {job_id}")


def read_project_job_log(project_id: str, job_id: str) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    log_path = _log_path(project_dir, job_id)
    if not log_path.exists():
        raise FileNotFoundError(f"job log not found: {job_id}")
    return {
        "project_id": project_id,
        "job_id": job_id,
        "relative_path": _relative(log_path, project_dir),
        "content": log_path.read_text(encoding="utf-8", errors="replace"),
    }


def _base_job_record(project_id: str, job_id: str, job_type: str, payload: dict[str, Any], status: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": "researchagent.job.v2",
        "project_id": project_id,
        "job_id": job_id,
        "job_type": job_type,
        "status": status,
        "progress": 0.0,
        "current_step": "queued" if status == "queued" else "started",
        "created_at": now,
        "started_at": None if status == "queued" else now,
        "completed_at": None,
        "payload": _safe_payload(payload),
        "outputs": [],
        "errors": [],
        "result": None,
        "cancel_requested": False,
        "cancelled_at": None,
        "execution_mode": "background" if status == "queued" else "synchronous",
        "limitations": [
            "Local MVP job runner records progress artifacts and supports cooperative cancellation.",
            "Cancellation requests are honored at checkpoint updates; already-running sandboxed subprocesses may finish or timeout first.",
            "Future workers can reuse this job artifact contract for async execution.",
        ],
    }


def _summary_event(project_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    job_id = str(record["job_id"])
    event = {
        "schema_version": "researchagent.job.event.v2",
        "project_id": record["project_id"],
        "job_id": job_id,
        "job_type": record["job_type"],
        "status": record["status"],
        "progress": record["progress"],
        "current_step": record["current_step"],
        "created_at": utc_now(),
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "cancel_requested": bool(record.get("cancel_requested")),
        "job_file": _relative(_job_path(project_dir, job_id), project_dir),
        "log_file": _relative(_log_path(project_dir, job_id), project_dir),
        "events_file": _relative(_events_path(project_dir, job_id), project_dir),
    }
    if record.get("outputs"):
        event["outputs"] = record.get("outputs")
    return event


def _run_existing_job_record(
    project_id: str,
    job_id: str,
    runner: Callable[[Callable[[str, float | None], None]], dict[str, Any]],
    *,
    append_final_event: bool = True,
) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    ensure_dir(project_dir / JOBS_DIR)
    path = _job_path(project_dir, job_id)
    record = _read_json(path, {})
    if not isinstance(record, dict) or record.get("job_id") != job_id:
        raise FileNotFoundError(f"job not found: {job_id}")
    log_path = _log_path(project_dir, job_id)
    existing_log = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else []
    log_lines: list[str] = list(existing_log)

    def persist() -> None:
        write_json(_job_path(project_dir, job_id), record)
        write_json(project_dir / LATEST_JOB_JSON, record)
        write_text(log_path, "\n".join(log_lines) + ("\n" if log_lines else ""))

    def assert_not_cancelled() -> None:
        if _is_cancel_requested(project_dir, job_id):
            record["cancel_requested"] = True
            raise JobCancelled("job cancellation requested")

    def update(step: str, progress: float | None = None) -> None:
        assert_not_cancelled()
        if progress is not None:
            record["progress"] = max(0.0, min(float(progress), 1.0))
        record["current_step"] = step
        if record.get("status") in {"queued", "cancelling"}:
            record["status"] = "running"
        log_lines.append(f"[{utc_now()}] {step}")
        _append_job_event(project_dir, record, "progress", step, {"progress": record.get("progress")})
        persist()

    with ACTIVE_JOB_LOCK:
        ACTIVE_JOB_IDS.add(job_id)
    try:
        if record.get("status") == "queued":
            record["status"] = "running"
            record["started_at"] = record.get("started_at") or utc_now()
        _append_job_event(project_dir, record, "started", "job started")
        persist()
        _append_jsonl(project_dir / JOBS_JSONL, _summary_event(project_dir, record))
        update("running", 0.05)
        result = runner(update)
        assert_not_cancelled()
        record["result"] = result
        if isinstance(result, dict):
            outputs = []
            run_payload = result.get("run")
            if isinstance(run_payload, dict):
                for key, value in run_payload.items():
                    if key.endswith("_file") and isinstance(value, str):
                        outputs.append(value)
                paper_outputs = run_payload.get("paper_outputs")
                if isinstance(paper_outputs, dict):
                    outputs.extend(value for value in paper_outputs.values() if isinstance(value, str))
            record["outputs"] = sorted(set(outputs))
        record["status"] = "completed"
        record["progress"] = 1.0
        record["current_step"] = "completed"
    except JobCancelled as exc:
        record["status"] = "cancelled"
        record["cancel_requested"] = True
        record["cancelled_at"] = utc_now()
        record["current_step"] = "cancelled"
        record["errors"].append({"type": exc.__class__.__name__, "message": str(exc)})
        log_lines.append(f"[{utc_now()}] cancellation acknowledged")
    except Exception as exc:  # pragma: no cover - defensive artifact path
        record["status"] = "failed"
        record["current_step"] = "failed"
        record["errors"].append({"type": exc.__class__.__name__, "message": str(exc)})
        log_lines.append(traceback.format_exc())
    finally:
        record["completed_at"] = utc_now()
        _append_job_event(project_dir, record, "terminal", f"job {record.get('status')}", {"outputs": record.get("outputs", []), "error_count": len(record.get("errors", []))})
        persist()
        if append_final_event:
            _append_jsonl(project_dir / JOBS_JSONL, _summary_event(project_dir, record))
        append_audit_event(
            project_dir,
            project_id,
            "run_project_job",
            f"Local job {record['job_type']} {record['status']}.",
            {
                "job_id": job_id,
                "job_type": record["job_type"],
                "status": record["status"],
                "outputs": record.get("outputs", []),
                "cancel_requested": bool(record.get("cancel_requested")),
            },
            source="api",
            event_category="job",
            risk_level="low" if record["status"] == "completed" else "medium",
            entity_type="job",
            entity_id=job_id,
        )
        with ACTIVE_JOB_LOCK:
            ACTIVE_JOB_IDS.discard(job_id)
    return record


def run_project_job(
    project_id: str,
    job_type: str,
    payload: dict[str, Any],
    runner: Callable[[Callable[[str, float | None], None]], dict[str, Any]],
) -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    ensure_dir(project_dir / JOBS_DIR)
    job_id = _job_id(job_type)
    record = _base_job_record(project_id, job_id, job_type, payload, "running")
    write_json(_job_path(project_dir, job_id), record)
    write_json(project_dir / LATEST_JOB_JSON, record)
    write_text(_log_path(project_dir, job_id), "")
    _append_job_event(project_dir, record, "created", "synchronous job created")
    _append_jsonl(project_dir / JOBS_JSONL, _summary_event(project_dir, record))
    return _run_existing_job_record(project_id, job_id, runner)


def start_project_job_background(
    project_id: str,
    job_type: str,
    payload: dict[str, Any],
    runner: Callable[[Callable[[str, float | None], None]], dict[str, Any]],
) -> dict[str, Any]:
    """Start an in-process local background job and return immediately.

    This is a local-MVP worker contract. It is intentionally lightweight and
    durable through JSON artifacts, while cancellation remains cooperative.
    """
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    ensure_dir(project_dir / JOBS_DIR)
    job_id = _job_id(job_type)
    record = _base_job_record(project_id, job_id, job_type, payload, "queued")
    write_json(_job_path(project_dir, job_id), record)
    write_json(project_dir / LATEST_JOB_JSON, record)
    write_text(_log_path(project_dir, job_id), f"[{utc_now()}] queued background job\n")
    _append_job_event(project_dir, record, "created", "background job queued")
    _append_jsonl(project_dir / JOBS_JSONL, _summary_event(project_dir, record))

    thread = threading.Thread(
        target=_run_existing_job_record,
        args=(project_id, job_id, runner),
        kwargs={"append_final_event": True},
        daemon=True,
        name=f"researchagent-{job_id}",
    )
    thread.start()
    return read_project_job(project_id, job_id)


def request_project_job_cancel(project_id: str, job_id: str, reason: str = "") -> dict[str, Any]:
    project_service.require_project(project_id)
    project_dir = storage_service.ensure_project_structure(project_id)
    record = read_project_job(project_id, job_id)
    status = str(record.get("status") or "unknown")
    now = utc_now()
    cancel_record = {
        "schema_version": "researchagent.job.cancel.v1",
        "project_id": project_id,
        "job_id": job_id,
        "requested_at": now,
        "reason": reason,
        "cooperative": True,
        "limitations": [
            "Cancellation is cooperative and checked at job progress checkpoints.",
            "Already-started subprocess or Docker sandbox runs may finish or timeout before cancellation is acknowledged.",
        ],
    }
    write_json(_cancel_path(project_dir, job_id), cancel_record)
    record["cancel_requested"] = True
    record["cancelled_at"] = now if status in {"queued", "cancelling"} else record.get("cancelled_at")
    if status == "queued":
        record["status"] = "cancelled"
        record["current_step"] = "cancelled before start"
        record["completed_at"] = now
    elif status == "running":
        record["status"] = "cancelling"
        record["current_step"] = "cancellation requested"
    elif status in {"completed", "failed", "cancelled"}:
        record["current_step"] = f"cancel requested after terminal status: {status}"
    write_json(_job_path(project_dir, job_id), record)
    write_json(project_dir / LATEST_JOB_JSON, record)
    _append_job_event(project_dir, record, "cancel_requested", reason or "cancellation requested")
    log_path = _log_path(project_dir, job_id)
    existing = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    write_text(log_path, existing + f"[{now}] cancellation requested: {reason}\n")
    _append_jsonl(project_dir / JOBS_JSONL, _summary_event(project_dir, record))
    append_audit_event(
        project_dir,
        project_id,
        "request_project_job_cancel",
        f"Cancellation requested for local job {job_id}.",
        {"job_id": job_id, "status": record.get("status"), "reason": reason},
        source="api",
        event_category="job",
        risk_level="medium",
        entity_type="job",
        entity_id=job_id,
    )
    return record
