from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from app.tools.auto_scientist.contracts import DOCKER_IMAGE_POLICY_JSON, SCHEMA_PREFIX, safe_id, utc_now, write_project_json
from app.tools.auto_scientist.generated_code_approval import (
    generated_code_is_approved,
    latest_generated_code_decision,
    source_sha256,
)
from app.tools.llm_client import llm_client
from app.tools.auto_scientist.experiment_code_writer import generate_experiment_code_source, normalize_codegen_strategy

GENERATED_CODE_TEMPLATE = "generated_code_smoke_test"
GENERATED_CODE_BASE_DIR = "auto_scientist/generated_code"
MAX_SOURCE_CHARS = 20_000
MAX_STDIO_CHARS = 12_000
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_MEMORY_MB = 512
DEFAULT_FILE_SIZE_MB = 8
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"
PROMPT_VERSION = "auto_scientist_experiment_codegen_v1"
DEFAULT_DOCKER_IMAGE_ALLOWLIST = {"python:3.11-slim"}

ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "collections",
    "csv",
    "datetime",
    "json",
    "math",
    "pathlib",
    "statistics",
    "typing",
}
FORBIDDEN_IMPORT_ROOTS = {
    "asyncio",
    "ctypes",
    "ftplib",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "pathlib2",
    "pickle",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "threading",
    "urllib",
}
FORBIDDEN_CALL_NAMES = {
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "__import__",
}
FORBIDDEN_ATTRIBUTE_NAMES = {
    "accept",
    "bind",
    "chmod",
    "chown",
    "connect",
    "delete",
    "exec",
    "fork",
    "kill",
    "link",
    "listen",
    "open",
    "popen",
    "recv",
    "remove",
    "rename",
    "replace",
    "request",
    "rmdir",
    "rmtree",
    "send",
    "spawn",
    "symlink",
    "system",
    "unlink",
    "urlopen",
    "write_bytes",
}


class GeneratedCodeSafetyError(ValueError):
    pass


def _truncate(value: str | bytes | None, limit: int = MAX_STDIO_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n... [truncated {len(value) - limit} chars]"


def _import_root(name: str) -> str:
    return name.split(".", 1)[0]


def scan_generated_python_source(source: str) -> dict[str, Any]:
    """Conservatively validate generated experiment code before execution.

    The scanner is intentionally a policy gate, not a complete sandbox. It is
    paired with either a short-lived local subprocess or an optional Docker
    runner. Docker mode is explicit and never pulls images automatically.
    """
    findings: list[str] = []
    if len(source) > MAX_SOURCE_CHARS:
        findings.append(f"source exceeds {MAX_SOURCE_CHARS} characters")
        return {"safe": False, "findings": findings, "import_roots": []}
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"safe": False, "findings": [f"syntax error: {exc.msg}"], "import_roots": []}

    import_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _import_root(alias.name)
                import_roots.add(root)
                if root in FORBIDDEN_IMPORT_ROOTS or root not in ALLOWED_IMPORT_ROOTS:
                    findings.append(f"forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = _import_root(module)
            import_roots.add(root)
            if root in FORBIDDEN_IMPORT_ROOTS or root not in ALLOWED_IMPORT_ROOTS:
                findings.append(f"forbidden import: {module}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALL_NAMES:
                findings.append(f"forbidden call: {func.id}")
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_ATTRIBUTE_NAMES:
                findings.append(f"forbidden attribute call: {func.attr}")
        elif isinstance(node, ast.Attribute):
            if node.attr in {"__dict__", "__class__", "__subclasses__", "__globals__"}:
                findings.append(f"forbidden introspection attribute: {node.attr}")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            findings.append("global/nonlocal statements are not allowed")

    return {"safe": not findings, "findings": sorted(set(findings)), "import_roots": sorted(import_roots)}


def generate_deterministic_experiment_source(config: dict[str, Any]) -> str:
    """Generate a bounded Python experiment script from local config.

    This wrapper preserves the historical public helper while delegating to the
    deterministic local experiment-code writer. The writer supports multiple
    strategies and still passes through the same scan/sandbox/result contract.
    """
    source, _metadata = generate_experiment_code_source(config)
    return source




def _source_generator_mode(config: dict[str, Any]) -> str:
    mode = str(config.get("generated_code_source_mode") or "deterministic").strip().lower()
    if config.get("generated_source"):
        return "provided"
    if mode not in {"deterministic", "mock_llm", "live_llm"}:
        return "deterministic"
    return mode


def _llm_codegen_messages(config: dict[str, Any], fallback_source: str) -> list[dict[str, str]]:
    request = {
        "task": "Generate a bounded Python experiment over project-local input.json only.",
        "topic": config.get("topic"),
        "research_question": config.get("research_question"),
        "constraints": [
            "Read only input.json from the current working directory.",
            "Write only outputs/result.json, outputs/metrics.json, and outputs/summary.md.",
            "Use only allowed imports: json, math, pathlib, statistics, collections, csv, datetime, typing.",
            "Do not use network, subprocess, os, sys, open, eval, exec, dynamic import, or file system traversal.",
            "Do not fabricate p-values, statistical significance, causal conclusions, DOI values, or verified references.",
            "Return JSON with source_code and safety_notes only.",
        ],
        "fallback_source_contract": fallback_source[:2000],
    }
    system = (
        "You generate safe local experiment code for ResearchAgent Auto Scientist. "
        "The code will be statically scanned and may require human approval before sandbox execution. "
        "Output strict JSON only."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
    ]


def generate_experiment_source_candidate(
    project_dir: Path,
    project_id: str,
    run_id: str,
    experiment_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Generate or load a candidate experiment source under a reviewable contract.

    The default path is deterministic and does not call an external provider. Live
    LLM code generation is optional through the existing llm_client and still goes
    through the same static scan, approval gate, sandbox, and artifact logging.
    """
    mode = _source_generator_mode(config)
    fallback_source, writer_metadata = generate_experiment_code_source(config)
    source = str(config.get("generated_source") or fallback_source)
    llm_status: dict[str, Any] | None = None
    safety_notes = [
        "Generated source is a candidate artifact, not trusted code.",
        "Static scan, approval policy, and sandbox execution are required before accepting results.",
    ]

    if mode in {"mock_llm", "live_llm"}:
        fallback = {
            "source_code": fallback_source,
            "safety_notes": [
                "Fallback deterministic source used unless a configured live LLM returns valid JSON.",
                "Code must read input.json and write outputs/result.json, outputs/metrics.json, outputs/summary.md.",
            ],
        }
        response = llm_client.chat_json(
            _llm_codegen_messages(config, fallback_source),
            fallback,
            prompt_version=PROMPT_VERSION,
        )
        parsed = response.parsed_json if isinstance(response.parsed_json, dict) else fallback
        source = str(parsed.get("source_code") or fallback_source)
        parsed_notes = parsed.get("safety_notes")
        if isinstance(parsed_notes, list):
            safety_notes.extend(str(item) for item in parsed_notes[:8])
        llm_status = {
            "mode": response.mode,
            "provider": response.provider,
            "model": response.model,
            "prompt_version": response.prompt_version,
            "status": response.status,
            "error": response.error,
        }

    source_hash = source_sha256(source)
    return {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_source_candidate.v1",
        "project_id": project_id,
        "run_id": safe_id(run_id),
        "experiment_id": safe_id(experiment_id),
        "created_at": utc_now(),
        "source_mode": mode,
        "source_hash": source_hash,
        "source_code": source,
        "prompt_version": PROMPT_VERSION if mode in {"mock_llm", "live_llm"} else None,
        "llm": llm_status,
        "writer": writer_metadata,
        "generated_code_strategy": normalize_codegen_strategy(str(config.get("generated_code_strategy") or "")),
        "safety_notes": safety_notes,
        "human_approval_recommended": mode in {"provided", "mock_llm", "live_llm"},
    }


def _generated_code_requires_approval(config: dict[str, Any], source_candidate: dict[str, Any]) -> bool:
    if config.get("generated_code_requires_approval") is True:
        return True
    if config.get("generated_code_requires_approval") is False:
        return False
    return str(source_candidate.get("source_mode")) in {"provided", "mock_llm", "live_llm"}

def _resource_preexec(memory_mb: int, file_size_mb: int, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
    if os.name == "nt":
        return None

    def _limit_resources() -> None:
        import resource

        memory_bytes = max(memory_mb, 64) * 1024 * 1024
        file_bytes = max(file_size_mb, 1) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_bytes, file_bytes))
        # Wall-clock timeout is enforced by subprocess.run(timeout=...).
        # Avoid RLIMIT_CPU here because some CI/container kernels account Python
        # startup CPU aggressively and can SIGXCPU tiny experiments.

    return _limit_resources


def _safe_relative(path: Path, project_dir: Path) -> str:
    return path.relative_to(project_dir).as_posix()


def _source_input_payload(project_dir: Path, project_id: str, config: dict[str, Any]) -> dict[str, Any]:
    chunks_path = project_dir / "literature" / "rag" / "chunks.jsonl"
    evidence_parts: list[str] = []
    source_passages: list[dict[str, Any]] = []
    if chunks_path.exists():
        for line in chunks_path.read_text(encoding="utf-8", errors="replace").splitlines()[:12]:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                text = str(record.get("text") or "")[:700]
                evidence_parts.append(text)
                source_passages.append(
                    {
                        "chunk_id": record.get("chunk_id"),
                        "source_file": record.get("source_file"),
                        "position_label": record.get("position_label"),
                        "metadata_trust_level": record.get("metadata_trust_level"),
                        "evidence_warning_flags": record.get("evidence_warning_flags") or [],
                        "text": text,
                    }
                )
    if not evidence_parts:
        generated_names = {"literature_review.md", "key_findings.json", "novelty_report.json", "literature_index.json"}
        literature_files = [
            path for path in sorted((project_dir / "literature").iterdir())
            if path.is_file() and path.name not in generated_names and path.suffix.lower() in {".txt", ".md", ".markdown"}
        ]
        for path in literature_files[:4]:
            text = path.read_text(encoding="utf-8", errors="replace")[:900]
            evidence_parts.append(text)
            source_passages.append({"chunk_id": path.stem, "source_file": f"literature/{path.name}", "position_label": "local text snippet", "text": text})

    claim_texts: list[str] = []
    claim_audit_path = project_dir / "provenance" / "claim_audit.json"
    if claim_audit_path.exists():
        try:
            claim_audit = json.loads(claim_audit_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            claim_audit = {}
        items = claim_audit.get("claim_audits") if isinstance(claim_audit, dict) else []
        if isinstance(items, list):
            for item in items[:20]:
                if isinstance(item, dict) and item.get("sentence"):
                    claim_texts.append(str(item.get("sentence"))[:500])
    if not claim_texts:
        for path in [project_dir / "manuscript" / "draft_full.md", project_dir / "manuscript" / "draft.md"]:
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                for sentence in text.replace("\n", " ").split(".")[:20]:
                    sentence = sentence.strip()
                    if len(sentence) > 40:
                        claim_texts.append(sentence[:500])
                break

    data_tables: list[dict[str, Any]] = []
    analysis_path = project_dir / "analysis" / "result_summary.json"
    if analysis_path.exists():
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            analysis = {}
        if isinstance(analysis, dict):
            data_tables.append(
                {
                    "relative_path": f"data/{analysis.get('source_data', 'demo_data.csv')}",
                    "row_count": analysis.get("row_count"),
                    "column_count": analysis.get("column_count"),
                    "numeric_columns": analysis.get("numeric_columns") or [],
                }
            )

    return {
        "schema_version": f"{SCHEMA_PREFIX}.generated_code_input.v1",
        "project_id": project_id,
        "created_at": utc_now(),
        "topic": config.get("topic"),
        "research_question": config.get("research_question"),
        "parent_experiment_id": config.get("parent_experiment_id"),
        "tree_depth": config.get("tree_depth"),
        "generated_code_strategy": normalize_codegen_strategy(str(config.get("generated_code_strategy") or "")),
        "evidence_text": "\n\n".join(evidence_parts)[:8_000],
        "source_passages": source_passages[:12],
        "claim_texts": claim_texts[:20],
        "data_tables": data_tables[:12],
        "notes": [
            "Input contains only project-local extracted text snippets and artifact summaries.",
            "Generated-code sandbox has no network permission by policy and is statically scanned before execution.",
            "Input payload is a bounded derivative artifact, not raw unlimited project data.",
        ],
    }


def _base_output_files(project_dir: Path, paths: list[Path]) -> list[str]:
    output_files: list[str] = []
    for path in paths:
        if path.exists():
            output_files.append(_safe_relative(path, project_dir))
    return output_files


def _read_result_payload(result_json_path: Path, summary_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[Any], str]:
    result_payload: dict[str, Any] = {}
    if result_json_path.exists():
        try:
            loaded = json.loads(result_json_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                result_payload = loaded
        except json.JSONDecodeError:
            result_payload = {}
    metrics = result_payload.get("metrics") if isinstance(result_payload.get("metrics"), dict) else {}
    claims = result_payload.get("claims") if isinstance(result_payload.get("claims"), list) else []
    summary_markdown = str(result_payload.get("summary_markdown") or "")
    if not summary_markdown and summary_path.exists():
        summary_markdown = summary_path.read_text(encoding="utf-8", errors="replace")
    return result_payload, metrics, claims, summary_markdown


def _write_rejected_result(
    project_dir: Path,
    base_dir: Path,
    source_path: Path,
    input_path: Path,
    scan: dict[str, Any],
    requested_timeout_seconds: int,
    timeout_seconds: int,
    memory_mb: int,
    sandbox_mode: str,
) -> dict[str, Any]:
    payload = {
        "status": "rejected_by_static_scan",
        "metrics": {"static_scan_safe": False, "finding_count": len(scan["findings"])},
        "claims": [],
        "summary_markdown": "# Generated-code experiment rejected\n\n" + "\n".join(f"- {item}" for item in scan["findings"]),
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "sandbox": {
            "enabled": True,
            "runner": sandbox_mode,
            "static_scan": scan,
            "requested_timeout_seconds": requested_timeout_seconds,
            "timeout_seconds": timeout_seconds,
            "memory_mb": memory_mb,
            "network_disabled_by_policy": True,
            "output_files": [_safe_relative(source_path, project_dir), _safe_relative(input_path, project_dir)],
        },
    }
    write_project_json(project_dir, _safe_relative(base_dir / "sandbox_result.json", project_dir), payload)
    return payload


def _subprocess_runner(
    project_dir: Path,
    base_dir: Path,
    output_dir: Path,
    source_path: Path,
    input_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    scan: dict[str, Any],
    requested_timeout_seconds: int,
    timeout_seconds: int,
    memory_mb: int,
    file_size_mb: int,
) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "RESEARCHAGENT_SANDBOX": "1",
        "NO_PROXY": "*",
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "experiment.py"],
            cwd=base_dir,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            preexec_fn=_resource_preexec(memory_mb, file_size_mb, timeout_seconds),
            check=False,
        )
        stdout_path.write_text(_truncate(completed.stdout), encoding="utf-8")
        stderr_path.write_text(_truncate(completed.stderr), encoding="utf-8")
        return_code = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(_truncate(exc.stdout), encoding="utf-8")
        stderr_path.write_text(_truncate((exc.stderr or b"") + b"\nTIMEOUT"), encoding="utf-8")
        return_code = -1
        timed_out = True

    result_json_path = output_dir / "result.json"
    metrics_json_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.md"
    result_payload, metrics, claims, summary_markdown = _read_result_payload(result_json_path, summary_path)
    status = "completed" if return_code == 0 and result_payload else "failed"
    if timed_out:
        status = "timeout"
    output_files = _base_output_files(project_dir, [source_path, input_path, stdout_path, stderr_path, result_json_path, metrics_json_path, summary_path])
    payload = {
        "status": status,
        "metrics": metrics,
        "claims": claims,
        "summary_markdown": summary_markdown or f"# Generated-code sandbox experiment\n\nStatus: {status}\n\nReturn code: {return_code}\n",
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "sandbox": {
            "enabled": True,
            "runner": "python_subprocess_static_scan_resource_limits",
            "static_scan": scan,
            "requested_timeout_seconds": requested_timeout_seconds,
            "timeout_seconds": timeout_seconds,
            "memory_mb": memory_mb,
            "max_file_size_mb": file_size_mb,
            "network_disabled_by_policy": True,
            "return_code": return_code,
            "timed_out": timed_out,
            "output_files": output_files,
        },
    }
    write_project_json(project_dir, _safe_relative(base_dir / "sandbox_result.json", project_dir), payload)
    return payload


def _docker_available(image: str, allowlist: set[str] | None = None) -> tuple[bool, str]:
    allowlist = allowlist or DEFAULT_DOCKER_IMAGE_ALLOWLIST
    if image not in allowlist:
        return False, f"docker image not allowed by local policy: {image}"
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, "docker binary not found"
    try:
        subprocess.run([docker_bin, "version", "--format", "{{.Server.Version}}"], text=True, capture_output=True, timeout=3, check=True)
    except Exception as exc:
        return False, f"docker daemon unavailable: {exc.__class__.__name__}"
    try:
        subprocess.run([docker_bin, "image", "inspect", image], text=True, capture_output=True, timeout=5, check=True)
    except Exception:
        return False, f"docker image not available locally: {image}; no image pull is attempted"
    return True, docker_bin


def _docker_runner(
    project_dir: Path,
    base_dir: Path,
    output_dir: Path,
    source_path: Path,
    input_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    scan: dict[str, Any],
    requested_timeout_seconds: int,
    timeout_seconds: int,
    memory_mb: int,
    file_size_mb: int,
    docker_image: str,
    docker_image_allowlist: set[str] | None = None,
) -> dict[str, Any]:
    docker_image_allowlist = docker_image_allowlist or DEFAULT_DOCKER_IMAGE_ALLOWLIST
    docker_ok, docker_info = _docker_available(docker_image, docker_image_allowlist)
    if not docker_ok:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(docker_info, encoding="utf-8")
        output_files = _base_output_files(project_dir, [source_path, input_path, stdout_path, stderr_path])
        payload = {
            "status": "docker_unavailable",
            "metrics": {"docker_available": False},
            "claims": [],
            "summary_markdown": f"# Docker sandbox unavailable\n\n{docker_info}\n",
            "generated_code_execution": True,
            "arbitrary_code_execution": False,
            "sandbox": {
                "enabled": False,
                "runner": "docker_network_none_unavailable",
                "docker_image": docker_image,
                "docker_image_allowlist": sorted(docker_image_allowlist),
                "docker_image_allowed": docker_image in docker_image_allowlist,
                "docker_available": False,
                "docker_unavailable_reason": docker_info,
                "static_scan": scan,
                "network_disabled_by_policy": True,
                "network_disabled_by_docker": False,
                "timeout_seconds": timeout_seconds,
                "memory_mb": memory_mb,
                "output_files": output_files,
            },
        }
        write_project_json(project_dir, _safe_relative(base_dir / "sandbox_result.json", project_dir), payload)
        return payload

    cmd = [
        str(docker_info),
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        f"{max(memory_mb, 64)}m",
        "--pids-limit",
        "64",
        "--cpus",
        "1",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "-v",
        f"{base_dir.resolve()}:/workspace:rw",
        "-w",
        "/workspace",
        docker_image,
        "python",
        "-I",
        "-S",
        "experiment.py",
    ]
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_seconds, check=False)
        stdout_path.write_text(_truncate(completed.stdout), encoding="utf-8")
        stderr_path.write_text(_truncate(completed.stderr), encoding="utf-8")
        return_code = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(_truncate(exc.stdout), encoding="utf-8")
        stderr_path.write_text(_truncate((exc.stderr or b"") + b"\nTIMEOUT"), encoding="utf-8")
        return_code = -1
        timed_out = True

    result_json_path = output_dir / "result.json"
    metrics_json_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.md"
    result_payload, metrics, claims, summary_markdown = _read_result_payload(result_json_path, summary_path)
    status = "completed" if return_code == 0 and result_payload else "failed"
    if timed_out:
        status = "timeout"
    output_files = _base_output_files(project_dir, [source_path, input_path, stdout_path, stderr_path, result_json_path, metrics_json_path, summary_path])
    payload = {
        "status": status,
        "metrics": metrics,
        "claims": claims,
        "summary_markdown": summary_markdown or f"# Docker generated-code sandbox experiment\n\nStatus: {status}\n\nReturn code: {return_code}\n",
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "sandbox": {
            "enabled": True,
            "runner": "docker_network_none_static_scan_resource_limits",
            "docker_image": docker_image,
            "docker_image_allowlist": sorted(docker_image_allowlist),
            "docker_image_allowed": docker_image in docker_image_allowlist,
            "docker_available": True,
            "static_scan": scan,
            "requested_timeout_seconds": requested_timeout_seconds,
            "timeout_seconds": timeout_seconds,
            "memory_mb": memory_mb,
            "max_file_size_mb": file_size_mb,
            "network_disabled_by_policy": True,
            "network_disabled_by_docker": True,
            "return_code": return_code,
            "timed_out": timed_out,
            "output_files": output_files,
        },
    }
    write_project_json(project_dir, _safe_relative(base_dir / "sandbox_result.json", project_dir), payload)
    return payload




def _docker_image_allowlist(config: dict[str, Any]) -> set[str]:
    configured = config.get("generated_code_docker_image_allowlist")
    if isinstance(configured, list):
        items = {str(item).strip() for item in configured if str(item).strip()}
        return items or set(DEFAULT_DOCKER_IMAGE_ALLOWLIST)
    env_value = os.environ.get("AUTO_SCIENTIST_DOCKER_IMAGE_ALLOWLIST", "")
    if env_value.strip():
        return {item.strip() for item in env_value.split(",") if item.strip()} or set(DEFAULT_DOCKER_IMAGE_ALLOWLIST)
    return set(DEFAULT_DOCKER_IMAGE_ALLOWLIST)


def _write_docker_image_policy(project_dir: Path, config: dict[str, Any], docker_image: str) -> None:
    allowlist = _docker_image_allowlist(config)
    payload = {
        "schema_version": f"{SCHEMA_PREFIX}.docker_image_policy.v1",
        "created_at": utc_now(),
        "policy_file": DOCKER_IMAGE_POLICY_JSON,
        "requested_image": docker_image,
        "allowed_images": sorted(allowlist),
        "requested_image_allowed": docker_image in allowlist,
        "automatic_image_pull": False,
        "notes": [
            "Docker sandbox mode never pulls images automatically.",
            "Images outside the allowlist are rejected before docker execution.",
        ],
    }
    write_project_json(project_dir, DOCKER_IMAGE_POLICY_JSON, payload)


def _write_pending_approval_result(
    project_dir: Path,
    base_dir: Path,
    source_path: Path,
    input_path: Path,
    proposal_path: Path,
    scan: dict[str, Any],
    source_candidate: dict[str, Any],
    requested_timeout_seconds: int,
    timeout_seconds: int,
    memory_mb: int,
    sandbox_mode: str,
    latest_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    status = "rejected_by_human_approval" if latest_decision and latest_decision.get("decision") == "rejected" else "pending_human_approval"
    reason = latest_decision.get("reason") if isinstance(latest_decision, dict) else "Generated code requires recorded human approval before sandbox execution."
    output_files = _base_output_files(project_dir, [source_path, input_path, proposal_path])
    payload = {
        "status": status,
        "metrics": {"approval_required": True, "approved": False},
        "claims": [],
        "summary_markdown": (
            "# Generated-code experiment approval required\n\n"
            f"Status: {status}\n\n"
            f"Reason: {reason or 'approval required'}\n"
        ),
        "generated_code_execution": True,
        "arbitrary_code_execution": False,
        "source_mode": source_candidate.get("source_mode"),
        "source_hash": source_candidate.get("source_hash"),
        "approval_required": True,
        "latest_approval_decision": latest_decision,
        "sandbox": {
            "enabled": False,
            "runner": f"{sandbox_mode}_pending_human_approval",
            "static_scan": scan,
            "requested_timeout_seconds": requested_timeout_seconds,
            "timeout_seconds": timeout_seconds,
            "memory_mb": memory_mb,
            "network_disabled_by_policy": True,
            "output_files": output_files,
        },
    }
    write_project_json(project_dir, _safe_relative(base_dir / "sandbox_result.json", project_dir), payload)
    return payload



def _annotate_source_contract(result: dict[str, Any], source_candidate: dict[str, Any], approval_required: bool) -> dict[str, Any]:
    result.setdefault("source_mode", source_candidate.get("source_mode"))
    result.setdefault("source_hash", source_candidate.get("source_hash"))
    result.setdefault("approval_required", approval_required)
    result.setdefault("source_prompt_version", source_candidate.get("prompt_version"))
    if source_candidate.get("llm") is not None:
        result.setdefault("source_llm", source_candidate.get("llm"))
    return result

def run_generated_code_experiment(
    project_dir: Path,
    project_id: str,
    run_id: str,
    experiment_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    requested_timeout_seconds = int(config.get("generated_code_timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
    timeout_seconds = max(requested_timeout_seconds, 15)
    memory_mb = int(config.get("generated_code_max_memory_mb") or DEFAULT_MEMORY_MB)
    file_size_mb = int(config.get("generated_code_max_file_size_mb") or DEFAULT_FILE_SIZE_MB)
    sandbox_mode = str(config.get("generated_code_sandbox_mode") or "subprocess").strip().lower()
    if sandbox_mode not in {"subprocess", "docker"}:
        sandbox_mode = "subprocess"
    docker_image = str(config.get("generated_code_docker_image") or DEFAULT_DOCKER_IMAGE).strip() or DEFAULT_DOCKER_IMAGE

    base_dir = project_dir / GENERATED_CODE_BASE_DIR / safe_id(run_id) / safe_id(experiment_id)
    output_dir = base_dir / "outputs"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_candidate = generate_experiment_source_candidate(
        project_dir,
        project_id,
        run_id,
        experiment_id,
        config,
    )
    source = str(source_candidate["source_code"])
    scan = scan_generated_python_source(source)
    source_path = base_dir / "experiment.py"
    input_path = base_dir / "input.json"
    stdout_path = base_dir / "stdout.txt"
    stderr_path = base_dir / "stderr.txt"
    proposal_path = base_dir / "code_proposal.json"
    source_path.write_text(source, encoding="utf-8")
    input_payload = _source_input_payload(project_dir, project_id, config)
    input_path.write_text(json.dumps(input_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    proposal_payload = {k: v for k, v in source_candidate.items() if k != "source_code"}
    proposal_payload.update(
        {
            "source_file": _safe_relative(source_path, project_dir),
            "input_file": _safe_relative(input_path, project_dir),
            "static_scan": scan,
        }
    )
    proposal_path.write_text(json.dumps(proposal_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if sandbox_mode == "docker":
        _write_docker_image_policy(project_dir, config, docker_image)

    if not scan["safe"]:
        return _write_rejected_result(
            project_dir,
            base_dir,
            source_path,
            input_path,
            scan,
            requested_timeout_seconds,
            timeout_seconds,
            memory_mb,
            sandbox_mode,
        )

    approval_required = _generated_code_requires_approval(config, source_candidate)
    source_hash = str(source_candidate["source_hash"])
    latest_decision = latest_generated_code_decision(project_dir, run_id, experiment_id, source_hash)
    approved = bool(config.get("generated_code_approved")) or generated_code_is_approved(
        project_dir,
        run_id,
        experiment_id,
        source_hash,
    )
    if approval_required and not approved:
        return _write_pending_approval_result(
            project_dir,
            base_dir,
            source_path,
            input_path,
            proposal_path,
            scan,
            source_candidate,
            requested_timeout_seconds,
            timeout_seconds,
            memory_mb,
            sandbox_mode,
            latest_decision,
        )

    if sandbox_mode == "docker":
        docker_result = _docker_runner(
            project_dir,
            base_dir,
            output_dir,
            source_path,
            input_path,
            stdout_path,
            stderr_path,
            scan,
            requested_timeout_seconds,
            timeout_seconds,
            memory_mb,
            file_size_mb,
            docker_image,
            _docker_image_allowlist(config),
        )
        return _annotate_source_contract(docker_result, source_candidate, approval_required)

    subprocess_result = _subprocess_runner(
        project_dir,
        base_dir,
        output_dir,
        source_path,
        input_path,
        stdout_path,
        stderr_path,
        scan,
        requested_timeout_seconds,
        timeout_seconds,
        memory_mb,
        file_size_mb,
    )
    return _annotate_source_contract(subprocess_result, source_candidate, approval_required)
