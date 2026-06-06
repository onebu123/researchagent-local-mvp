from __future__ import annotations

from app.agents.base import BaseAgent
from app.tools.literature_index import build_literature_index, read_indexed_literature_texts
from app.workflows.state import ResearchState


class LiteratureAgent(BaseAgent):
    name = "Literature Agent"
    description = "读取文献索引、解析文本和 PDF 质量信息，生成可审计的文献综述草稿。"

    def run(self, state: ResearchState) -> ResearchState:
        self.log(state, "building literature index and reading parsed texts")
        index = build_literature_index(state.project_dir)
        indexed_texts = read_indexed_literature_texts(state.project_dir)
        state.literature_index = index
        state.literature_files = [entry["source_file"] for entry in index]

        if not indexed_texts:
            state.literature_is_placeholder = True
            source_note = "placeholder literature summary"
            combined = (
                "当前项目尚未上传可解析文献。以下内容为 placeholder literature summary，"
                "仅用于跑通工作流，不可作为真实引用或研究结论。"
            )
        else:
            combined = "\n\n".join(
                (
                    f"## Source: {entry['literature_id']} / {entry['source_file']}\n"
                    f"metadata_status={entry['metadata_status']}; "
                    f"parse_status={entry.get('parse_status', 'not_applicable')}; "
                    f"quality_label={entry.get('quality_label', 'unknown')}; "
                    f"quality_score={entry.get('quality_score', 'unknown')}\n"
                    f"{text[:2400]}"
                )
                for entry, text in indexed_texts
            )
            source_note = "uploaded or demo literature summary"
            state.literature_is_placeholder = any(
                entry.get("metadata_status") == "placeholder"
                or not entry.get("human_verified", False)
                for entry in index
            )

        placeholder_count = sum(
            1 for entry in index if entry.get("metadata_status") == "placeholder"
        )
        failed_parse_count = sum(
            1
            for entry in index
            if entry.get("source_type") == "pdf" and entry.get("parse_status") != "success"
        )
        low_quality_pdf_records = [
            entry.get("literature_id", entry.get("source_file", "unknown"))
            for entry in index
            if entry.get("source_type") == "pdf"
            and (
                entry.get("quality_label") in {"low", "failed"}
                or entry.get("needs_manual_review") is True
            )
        ]
        low_quality_page_records = []
        for entry in index:
            if entry.get("source_type") != "pdf":
                continue
            for page in entry.get("pages", []):
                if isinstance(page, dict) and page.get("quality_signal") in {"low", "empty"}:
                    low_quality_page_records.append(
                        {
                            "literature_id": entry.get("literature_id"),
                            "page_number": page.get("page_number"),
                            "quality_signal": page.get("quality_signal"),
                            "ocr_status": (page.get("ocr") or {}).get("ocr_status"),
                        }
                    )
        quality_note = (
            "PDF 解析质量存在风险，低质量或需要人工复核的记录为："
            + ", ".join(low_quality_pdf_records)
            if low_quality_pdf_records
            else "PDF 解析质量未发现低质量风险。"
        )

        review = f"""# 文献综述草稿

> 来源说明：{source_note}。v0.3 会建立文献 metadata 与 PDF parse quality 结构，但不会联网核验 DOI、作者、年份、期刊或页码。

## 文献索引状态

- 文献记录数量：{len(index)}
- placeholder metadata 数量：{placeholder_count}
- PDF 解析失败或未支持数量：{failed_parse_count}
- PDF 低质量或需人工复核数量：{len(low_quality_pdf_records)}
- 人工核验记录数量：{sum(1 for entry in index if entry.get("human_verified"))}

## PDF 解析质量提示

{quality_note}

## 研究背景

围绕 {state.project_name}，现有资料可用于早期草稿中的背景梳理和问题组织。当前系统只基于项目内上传或 demo 文献文本做摘要，不伪造真实引用，也不把 placeholder metadata 当成已核验参考文献。

## 关键发现

1. 项目 CSV 可支持描述性分析和图表 provenance。
2. 图表和统计描述必须来自项目数据、分析摘要与 figure provenance。
3. placeholder 文献只能进入 Placeholder literature records，不能写成真实 DOI、期刊或年份引用。
4. PDF 解析质量低或需要人工复核时，不能把解析文本当作可靠全文来源。

## 研究空白

当前证据链仍缺少经过人工核验的真实文献 metadata、完整实验记录、正式引用数据和统计检验。

## 已读取文本摘要

{combined}
"""
        key_findings = {
            "source_note": source_note,
            "placeholder": state.literature_is_placeholder,
            "literature_count": len(index),
            "placeholder_count": placeholder_count,
            "failed_parse_count": failed_parse_count,
            "low_quality_pdf_records": low_quality_pdf_records,
            "low_quality_page_records": low_quality_page_records,
            "findings": [
                "项目 CSV 可以支持描述性分析和图表 provenance。",
                "当前系统不会伪造 DOI、作者、年份、期刊、p 值或因果结论。",
                "所有 placeholder 文献都需要人工核验后才能作为正式引用。",
                "低质量 PDF 解析结果需要人工复核。",
            ],
            "gaps": ["真实文献 metadata", "统计检验", "人工 evidence 审核", "PDF 解析质量复核"],
        }
        state.literature_review = review
        self.save_output(
            state,
            "literature/literature_review.md",
            review,
            "literature",
            "文献综述草稿",
        )
        self.save_output(
            state,
            "literature/key_findings.json",
            key_findings,
            "literature",
            "关键发现",
        )
        self.record_output(
            state,
            "literature/literature_index.json",
            "literature",
            "文献元数据索引",
            "application/json",
        )
        return state
