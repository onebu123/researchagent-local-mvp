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

## v1.3 RAG Quality

v1.3 在 `Literature Intelligence` 分组新增 `RAG Quality`：
- `Literature RAG` 默认使用 `local_hybrid`，同时保留 `local_keyword` fallback。
- `RAG Quality` 展示 `chunk_quality_report.json`、`retrieval_eval_set.json` 和 `retrieval_eval_report.json`。
- `Run Retrieval Eval` 使用本地 deterministic eval cases，不调用外部网络、embedding 服务或向量数据库。
- source passage 会显示 score breakdown：keyword、n-gram、metadata trust、chunk quality。

v1.3 输出仅用于本地检索质量排查。高 hit@k 或高 quality score 不代表科学事实成立、引用已验证、生产级检索质量或 peer-review-ready。

v1.3 验证命令：
```bash
python scripts/run_demo.py
python scripts/validate_v13.py
```
## v1.4 Statistical Assistant

v1.4 在右侧 `Analysis` 分组新增 `Statistical Assistant`：

- `Generate Local Report` 会基于本地 `analysis/result_summary.json` 和 `analysis/processed_data.csv` 生成 `analysis/statistical_assistant_report.json`。
- 面板展示 dataset health、variable role suggestions、descriptive cards、association candidates、method suggestions 和 guardrails。
- 后端不可用时仍会显示 mock fallback，便于本地 demo。
- Statistical Assistant is descriptive only: it does not generate p-values, does not claim statistical significance, and does not perform causal inference.

v1.4 验证命令：

```bash
python scripts/run_demo.py
python scripts/validate_v14.py
```

## ResearchAgent v1.5 Workspace Export

v1.5 在右侧工具区新增 `Workspace Export`。建议流程：

1. 运行 `python scripts/run_demo.py` 生成本地 demo 产物。
2. 打开前端首页，点击 `Workspace Export`。
3. 点击 `Generate docs` 生成本地导出文件。
4. 点击 `Refresh` 查看最新 `workspace_export_manifest.json`。
5. 运行 `python scripts/validate_v15.py` 做本地验收。

生成文件：

- `exports/workspace/research_workspace_export.docx`
- `exports/workspace/research_workspace_export.tex`
- `exports/workspace/trust_report.md`
- `exports/workspace/trust_report.json`
- `exports/workspace/workspace_export_manifest.json`

`research_workspace_export.docx` 用于人工审阅本地 workspace 摘要；`research_workspace_export.tex` 只是 LaTeX source，不执行完整编译；`trust_report.json` 和 `trust_report.md` 汇总 local MVP 证据、来源文件、audit hash chain 状态和 caveats。后端不可用时，前端仍显示 mock fallback，但真实文件生成必须调用后端 API。

Workspace Export 不会把 candidate 或 placeholder references 升级为正式引用，不会生成 DOI、p-values、significance、causal claims 或 OCR output，也不作为 production、compliance 或 peer review 证据。

## ResearchAgent v1.6 UX consolidation

v1.6 在首页新增 `Workspace Readiness`，用于把常用本地工作区状态集中到首屏：

- runtime mode：显示当前 demo 以 `Mock fallback active` 为默认可用状态。
- workflow：提示本地 pipeline 仍依赖已有 artifacts 和人工复核。
- trust：跳转到 `Global Trust Dashboard` 查看证据链和 caveats。
- exports：跳转到 `Workspace Export` 查看 Word、LaTeX 和 trust report 交付物。

推荐流程：

1. 运行 `python scripts/run_demo.py` 生成本地 demo artifacts。
2. 打开首页，先查看 `Workspace Readiness`。
3. 点击 `Open Global Trust`、`Review RAG Quality`、`Open Statistical Assistant` 或 `Open Workspace Export` 进入已有抽屉面板。
4. 运行 `python scripts/validate_v16.py` 做本地验收。

v1.6 不新增登录、数据库、任务队列、部署流程或后端 UX API。后端不可用时，前端继续使用 mock fallback，因此无 API key、无外网也能演示基本界面。
