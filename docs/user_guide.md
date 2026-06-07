# ResearchAgent v1.0 用户指南

## 使用入口

打开前端后，首页会显示 `Local MVP Overview`。这里集中展示项目状态、Global Trust Summary、v1.0 readiness、blocking items、最新 manuscript version 和最新 project export。

右侧工具入口按模块分组：

- Overview：Global Trust Dashboard、Release Readiness、Project Export、Validate Local MVP。
- Evidence：证据链和 evidence claim review。
- Manuscript：patch、version、diff、reviewer closure、issue resolution。
- Literature：literature metadata、history、diff、batch review、revert preview、PDF quality。
- Analysis：analysis provenance、comparison、timeline。
- Audit-Export：audit log、hash chain verify、audit export、filtered export、run history。

## 推荐流程

1. 运行 `python scripts/seed_demo.py` 创建 demo 项目。
2. 运行 `python scripts/run_demo.py` 生成本地产物。
3. 打开前端首页，先看 `Local MVP Overview`。
4. 打开 `Global Trust Dashboard`，检查 blocking items。
5. 打开 `Release Readiness`，确认 local MVP checks 和生产化缺口。
6. 打开 `Project Export`，生成项目 zip。
7. 运行 `python scripts/validate_v1.py` 做最终验收。

## 后端不可用时

前端保留 mock fallback。后端 API 断开时，核心面板仍可打开，但显示的是示例数据。真正导出 zip、运行 workflow、读取项目文件必须启动后端。

## 数据位置

- demo 项目：`projects/demo_project`
- 项目导出：`projects/demo_project/exports`
- 后端 SQLite：`projects/research_agent.sqlite3`
- 前端测试报告：`apps/web/playwright-report`，默认被 `.gitignore` 忽略

## v1.1 Literature Intelligence

右侧工具区新增 `Literature Intelligence` 分组：

- `LLM Settings`：查看 mock/live 状态、模型、provider、timeout/retry 和 Prompt Registry；不会显示 API key。
- `Prompt Registry`：同入口展示版本化 prompt 文件。
- `Literature RAG`：构建本地 keyword RAG index，并基于真实 chunk 生成带 `source_passages` 的回答草稿。
- `Source Passage Evidence`：查看 RAG answer 与 `chunk_id` 的来源绑定。
- `Metadata Lookup`：默认 `mock_fixture`，只生成候选与 warning，不修改 `literature_index.json`。
- `BibTeX`：只为 verified + human_verified 文献生成正式 BibTeX；placeholder 只写注释。
- `Citation Support`：用本地 source passage 检查 claim 支持状态，不证明科学事实。
- `LLM Call Log`：查看项目级 LLM 调用摘要、hash、token/cost 占位和状态。

v1.1 demo：

```bash
python scripts/run_demo.py
python scripts/validate_v11.py
```

## 常用命令

```bash
python scripts/start_local_dev.py
python scripts/seed_demo.py
python scripts/run_demo.py
python scripts/export_project_zip.py --project-id demo_project
python scripts/validate_v1.py
python scripts/validate_v11.py
```

## v1.2 Reference Verification

v1.2 新增一组右侧抽屉入口：
- `Run Reference Verification`：使用 `mock_fixture` 生成本地 reference candidate 和 match score，不修改 `literature_index.json`。
- `Verification Results`：查看 `reference_verification_results.jsonl` 与 summary。
- `Approval Workflow`：记录 approved、rejected 或 needs_manual_check；默认不应用到索引。
- `Verified References`：查看 `manuscript/references_status.json` 与 `manuscript/references_section_preview.md`，不会覆盖 `manuscript/draft.md`。
- `Citation Grounding`：查看 `provenance/citation_grounding_report.json`，用于本地 passage grounding。
- `BibTeX Status`：查看 approved-only BibTeX 状态。

只有在 `Approval Workflow` 中明确选择 apply，并发送 `apply_to_literature_index=true`，系统才会把 approved candidate 写回 `literature_index.json`，同时记录 metadata history 和 audit log。正式 References 与正式 BibTeX entry 只来自 `reference_verification_status=approved`、`metadata_status=verified`、`human_verified=true` 的记录。

v1.2 验证命令：
```bash
python scripts/run_demo.py
python scripts/validate_v12.py
```
