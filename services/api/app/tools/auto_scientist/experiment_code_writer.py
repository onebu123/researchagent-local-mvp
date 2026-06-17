from __future__ import annotations

import textwrap
from typing import Any

from app.tools.auto_scientist.contracts import SCHEMA_PREFIX, utc_now

CODEGEN_STRATEGIES = {
    "lexical_diagnostics",
    "retrieval_ablation",
    "claim_support_matrix",
    "descriptive_table_profile",
}


def normalize_codegen_strategy(value: str | None) -> str:
    strategy = (value or "lexical_diagnostics").strip().lower()
    return strategy if strategy in CODEGEN_STRATEGIES else "lexical_diagnostics"


def _common_helpers() -> str:
    return textwrap.dedent(
        r'''
        from __future__ import annotations

        import json
        import math
        from collections import Counter
        from pathlib import Path
        from statistics import mean

        def _tokens(text: str) -> list[str]:
            current: list[str] = []
            tokens: list[str] = []
            for ch in text.lower():
                if ch.isalnum() or ch in {"_", "-"}:
                    current.append(ch)
                elif current:
                    token = "".join(current)
                    if len(token) > 2:
                        tokens.append(token)
                    current = []
            if current:
                token = "".join(current)
                if len(token) > 2:
                    tokens.append(token)
            return tokens

        def _support_status(ratio: float) -> str:
            if ratio >= 0.35:
                return "supported"
            if ratio > 0:
                return "weakly_supported"
            return "unsupported"

        def _write_outputs(metrics: dict, result: dict) -> None:
            output_dir = Path("outputs")
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (output_dir / "summary.md").write_text(str(result.get("summary_markdown") or ""), encoding="utf-8")
        '''
    ).strip()


def _lexical_diagnostics_source(config: dict[str, Any]) -> str:
    topic = str(config.get("topic") or "local research project")[:180]
    question = str(config.get("research_question") or "What can the local evidence support?")[:400]
    return _common_helpers() + "\n\n" + textwrap.dedent(
        f'''
        TOPIC = {topic!r}
        QUESTION = {question!r}

        def main() -> None:
            payload = json.loads(Path("input.json").read_text(encoding="utf-8"))
            evidence_text = str(payload.get("evidence_text") or "")
            tokens = _tokens(evidence_text + " " + QUESTION + " " + TOPIC)
            counts = Counter(tokens)
            question_tokens = set(_tokens(QUESTION))
            evidence_tokens = set(_tokens(evidence_text))
            overlap = sorted(question_tokens & evidence_tokens)
            support_ratio = len(overlap) / max(len(question_tokens), 1)
            support_status = _support_status(support_ratio)
            token_lengths = [len(token) for token in tokens] or [0]
            metrics = {{
                "strategy": "lexical_diagnostics",
                "token_count": len(tokens),
                "unique_token_count": len(counts),
                "mean_token_length": round(mean(token_lengths), 3),
                "question_evidence_overlap": overlap,
                "question_evidence_overlap_ratio": round(support_ratio, 4),
                "sqrt_unique_tokens": round(math.sqrt(len(counts)), 4),
            }}
            result = {{
                "status": "completed",
                "metrics": metrics,
                "claims": [{{
                    "claim": "The generated-code writer computed bounded lexical diagnostics from project-local evidence text.",
                    "support_status": support_status,
                    "evidence": ["input.json", "outputs/result.json"],
                }}],
                "summary_markdown": "# Generated-code lexical diagnostics\\n\\n"
                + f"Topic: {{TOPIC}}\\n\\nQuestion: {{QUESTION}}\\n\\n"
                + f"Support status: {{support_status}}\\n\\nOverlap terms: {{', '.join(overlap) or 'none'}}\\n",
            }}
            _write_outputs(metrics, result)

        if __name__ == "__main__":
            main()
        '''
    ).strip() + "\n"


def _retrieval_ablation_source(config: dict[str, Any]) -> str:
    question = str(config.get("research_question") or "What can the local evidence support?")[:400]
    return _common_helpers() + "\n\n" + textwrap.dedent(
        f'''
        QUESTION = {question!r}

        def _chunk_score(question_tokens: set[str], text: str) -> float:
            chunk_tokens = set(_tokens(text))
            if not question_tokens:
                return 0.0
            return len(question_tokens & chunk_tokens) / max(len(question_tokens), 1)

        def main() -> None:
            payload = json.loads(Path("input.json").read_text(encoding="utf-8"))
            passages = payload.get("source_passages") if isinstance(payload.get("source_passages"), list) else []
            question_tokens = set(_tokens(QUESTION))
            scored = []
            for index, passage in enumerate(passages):
                if not isinstance(passage, dict):
                    continue
                text = str(passage.get("text") or "")
                score = _chunk_score(question_tokens, text)
                scored.append({{
                    "rank": index + 1,
                    "chunk_id": passage.get("chunk_id"),
                    "source_file": passage.get("source_file"),
                    "score": round(score, 4),
                    "warning_count": len(passage.get("evidence_warning_flags") or []),
                }})
            scored.sort(key=lambda item: (-float(item["score"]), str(item.get("chunk_id") or "")))
            top_score = float(scored[0]["score"]) if scored else 0.0
            support_status = _support_status(top_score)
            metrics = {{
                "strategy": "retrieval_ablation",
                "passage_count": len(scored),
                "top_score": round(top_score, 4),
                "mean_score": round(mean([float(item["score"]) for item in scored] or [0.0]), 4),
                "top_chunks": scored[:5],
            }}
            result = {{
                "status": "completed",
                "metrics": metrics,
                "claims": [{{
                    "claim": "A bounded retrieval ablation scored local source passages against the research question.",
                    "support_status": support_status,
                    "evidence": ["input.json", "outputs/metrics.json"],
                }}],
                "summary_markdown": "# Generated-code retrieval ablation\\n\\n"
                + f"Passages scored: {{len(scored)}}\\n\\nTop score: {{top_score:.4f}}\\n\\nSupport status: {{support_status}}\\n",
            }}
            _write_outputs(metrics, result)

        if __name__ == "__main__":
            main()
        '''
    ).strip() + "\n"


def _claim_support_matrix_source(config: dict[str, Any]) -> str:
    return _common_helpers() + "\n\n" + textwrap.dedent(
        r'''
        def _claim_ratio(claim: str, evidence_text: str) -> float:
            claim_tokens = set(_tokens(claim))
            evidence_tokens = set(_tokens(evidence_text))
            if not claim_tokens:
                return 0.0
            return len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)

        def main() -> None:
            payload = json.loads(Path("input.json").read_text(encoding="utf-8"))
            evidence_text = str(payload.get("evidence_text") or "")
            claims = payload.get("claim_texts") if isinstance(payload.get("claim_texts"), list) else []
            rows = []
            for index, claim in enumerate(claims[:20], start=1):
                claim_text = str(claim)
                ratio = _claim_ratio(claim_text, evidence_text)
                rows.append({
                    "claim_index": index,
                    "claim": claim_text[:220],
                    "support_ratio": round(ratio, 4),
                    "support_status": _support_status(ratio),
                })
            unsupported_count = sum(1 for item in rows if item["support_status"] == "unsupported")
            weak_count = sum(1 for item in rows if item["support_status"] == "weakly_supported")
            supported_count = sum(1 for item in rows if item["support_status"] == "supported")
            metrics = {
                "strategy": "claim_support_matrix",
                "claim_count": len(rows),
                "supported_count": supported_count,
                "weakly_supported_count": weak_count,
                "unsupported_count": unsupported_count,
                "claim_support_matrix": rows,
            }
            status = "supported" if supported_count and not unsupported_count else "weakly_supported" if rows else "unsupported"
            result = {
                "status": "completed",
                "metrics": metrics,
                "claims": [{
                    "claim": "The generated-code writer built a bounded claim/evidence support matrix from local artifacts.",
                    "support_status": status,
                    "evidence": ["input.json", "outputs/metrics.json"],
                }],
                "summary_markdown": "# Generated-code claim support matrix\n\n"
                + f"Claims checked: {len(rows)}\n\nSupported: {supported_count}\n\nWeak: {weak_count}\n\nUnsupported: {unsupported_count}\n",
            }
            _write_outputs(metrics, result)

        if __name__ == "__main__":
            main()
        '''
    ).strip() + "\n"


def _descriptive_table_profile_source(config: dict[str, Any]) -> str:
    return _common_helpers() + "\n\n" + textwrap.dedent(
        r'''
        def main() -> None:
            payload = json.loads(Path("input.json").read_text(encoding="utf-8"))
            tables = payload.get("data_tables") if isinstance(payload.get("data_tables"), list) else []
            rows = []
            for table in tables[:12]:
                if not isinstance(table, dict):
                    continue
                rows.append({
                    "relative_path": table.get("relative_path"),
                    "row_count": table.get("row_count"),
                    "column_count": table.get("column_count"),
                    "numeric_columns": table.get("numeric_columns") or [],
                })
            metrics = {
                "strategy": "descriptive_table_profile",
                "table_count": len(rows),
                "total_rows": sum(int(item.get("row_count") or 0) for item in rows),
                "tables": rows,
            }
            support_status = "supported" if rows else "unsupported"
            result = {
                "status": "completed",
                "metrics": metrics,
                "claims": [{
                    "claim": "The generated-code writer profiled project-local tabular data descriptively.",
                    "support_status": support_status,
                    "evidence": ["input.json", "outputs/metrics.json"],
                }],
                "summary_markdown": "# Generated-code descriptive table profile\n\n"
                + f"Tables profiled: {len(rows)}\n\nThis does not run statistical tests or infer causality.\n",
            }
            _write_outputs(metrics, result)

        if __name__ == "__main__":
            main()
        '''
    ).strip() + "\n"


def generate_experiment_code_source(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    strategy = normalize_codegen_strategy(str(config.get("generated_code_strategy") or ""))
    if strategy == "retrieval_ablation":
        source = _retrieval_ablation_source(config)
    elif strategy == "claim_support_matrix":
        source = _claim_support_matrix_source(config)
    elif strategy == "descriptive_table_profile":
        source = _descriptive_table_profile_source(config)
    else:
        source = _lexical_diagnostics_source(config)
    metadata = {
        "schema_version": f"{SCHEMA_PREFIX}.experiment_code_writer.v1",
        "created_at": utc_now(),
        "writer": "deterministic_local_experiment_code_writer",
        "strategy": strategy,
        "allowed_strategies": sorted(CODEGEN_STRATEGIES),
        "safety_contract": [
            "Read only input.json from the sandbox working directory.",
            "Write only outputs/result.json, outputs/metrics.json, and outputs/summary.md.",
            "No p-values, significance, causal claims, DOI values, or verified reference claims are fabricated.",
        ],
    }
    return source, metadata
