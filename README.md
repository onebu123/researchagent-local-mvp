# ResearchAgent v1.0 Local MVP

ResearchAgent 是一个本地运行的科研写作与审计辅助系统。v1.0 的目标是把 v0.1 到 v0.10 的本地 MVP 能力收口为可演示、可验证、可导出的版本。

v1.0 不是生产系统，也不声称论文内容真实、实验结论成立、引用已联网核验、或系统具备合规审计能力。

## 当前能力

- 本地项目工作流：文献、数据分析、图表、证据链、草稿、审稿问题、修订建议。
- Global Trust Dashboard：首页核心入口，汇总 evidence review、reviewer closure、audit hash chain、run history 和 blocking items。
- Release Readiness：展示 v1.0 Local MVP 就绪状态和生产化缺口。
- Project Export：生成安全 zip 包，包含项目核心产物并排除 `.env*`、密钥、缓存、运行时目录和绝对路径。
- Demo 项目：`demo_project` 可重复 seed、run、reset。
- Mock fallback：后端不可用时前端仍能打开核心面板。

## 技术栈

- 后端：FastAPI、Python、Pydantic、SQLite、本地文件系统。
- 前端：Next.js、React、TypeScript、Tailwind CSS、lucide-react、Playwright。
- 输出：Markdown、JSON、JSONL、CSV、PNG、SVG、TXT、ZIP。

## 快速启动

查看本地启动命令：

```bash
python scripts/start_local_dev.py
```

启动后端：

```bash
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

启动前端：

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3100
```

访问：

- 前端：`http://127.0.0.1:3100`
- 后端健康检查：`http://127.0.0.1:8000/health`

## Demo

创建 demo 数据：

```bash
python scripts/seed_demo.py
```

运行 demo workflow：

```bash
python scripts/run_demo.py
```

只重置 demo 项目：

```bash
python scripts/reset_demo.py --yes
```

`reset_demo.py` 只会删除并重建 `projects/demo_project`，不会删除代码、`.git`、`node_modules` 或其他项目。

## 导出项目 zip

命令行导出：

```bash
python scripts/export_project_zip.py --project-id demo_project
```

API：

- `POST /api/projects/{project_id}/export/zip`
- `GET /api/projects/{project_id}/export/zip`

zip 输出路径：

```text
projects/{project_id}/exports/researchagent_{project_id}_local_mvp_export_{timestamp}.zip
```

导出内容包含 manuscript、provenance、reviews、trust、analysis、figures、literature metadata、audit exports、run history 和 `README_EXPORT.md`。

## 验证

完整 v1.0 本地验证：

```bash
python scripts/validate_v1.py
```

手动分层验证：

```bash
python -m compileall services\api scripts
python -m pytest services\api\tests
python scripts\seed_demo.py
python scripts\run_demo.py
python scripts\validate_v01.py
python scripts\validate_v02.py
python scripts\validate_v03.py
python scripts\validate_v04.py
python scripts\validate_v05.py
python scripts\validate_v06.py
python scripts\validate_v07.py
python scripts\validate_v08.py
python scripts\validate_v09.py
python scripts\validate_v10.py
python scripts\validate_v1.py
cd apps\web
npm run typecheck
npm run build
npm audit
npx playwright test
```

## 重要限制

v1.0 Local MVP 不包含：

- 登录、鉴权、多租户、权限隔离。
- PostgreSQL、Redis、Celery、LangGraph、公网页面发布或生产部署。
- 生产数据库备份、恢复、迁移、任务队列、监控告警。
- 真实 DOI 校验、OCR、查重、AI 检测、科研仪器或外部科研软件集成。
- 科学事实验证、同行评审结论、合规认证或生产级防篡改审计。

详见 [local_mvp_limitations.md](docs/local_mvp_limitations.md)。

## ResearchAgent v1.1 Literature Intelligence

v1.1 在 v1.0 Local MVP 上增加本地文献智能能力：OpenAI-compatible LLM client、LLM call log、Prompt Registry、Literature RAG、Source Passage Evidence、Metadata Lookup、BibTeX draft 和 Citation Support。默认 `LLM_MODE=mock`，没有 API key 也可以运行 demo 和验证。

LLM 配置：

```bash
LLM_MODE=mock
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=openai-compatible
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=1
```

v1.1 API：

- `GET /api/system/llm/status`
- `POST /api/system/llm/test`
- `GET /api/system/prompts`
- `GET /api/projects/{project_id}/llm/calls`
- `POST /api/projects/{project_id}/literature/rag/build`
- `POST /api/projects/{project_id}/literature/rag/ask`
- `GET /api/projects/{project_id}/literature/rag/chunks`
- `GET /api/projects/{project_id}/literature/rag/answers`
- `GET /api/projects/{project_id}/provenance/source-passage-evidence`
- `POST /api/projects/{project_id}/literature/metadata-lookup`
- `GET /api/projects/{project_id}/literature/metadata-lookup/results`
- `POST /api/projects/{project_id}/literature/bibtex/generate`
- `GET /api/projects/{project_id}/literature/bibtex`
- `GET /api/projects/{project_id}/provenance/citation-support`

v1.1 验证：

```bash
python scripts/validate_v11.py
```

v1.1 不伪造 DOI、作者、年份、期刊、页码、p 值、统计显著性、因果关系或真实实验结论；RAG 只使用本地 parsed literature 文本；BibTeX 正式条目只来自 `metadata_status=verified` 且 `human_verified=true` 的记录。

## 文档

- [用户指南](docs/user_guide.md)
- [Demo 演示流程](docs/demo_walkthrough.md)
- [Local MVP 限制](docs/local_mvp_limitations.md)
- [v1.1 验收标准](docs/v1.1_acceptance_criteria.md)
- [v1.1 验收报告](docs/v1.1_acceptance_report.md)
- [GitHub 发布检查清单](docs/github_release_checklist.md)
- [v1.0 验收报告](docs/v1.0_acceptance_report.md)
- [GitHub 上传状态](docs/github_upload_status.md)

## ResearchAgent v1.2 Reference Verification

v1.2 在 v1.1 Literature Intelligence 基础上新增 Reference Verification、Reference Approval、Citation Grounding 和 Verified References 预览。默认 provider 是 `mock_fixture`，不需要 API key 或外部网络；`crossref_optional`、`semantic_scholar_optional`、`pubmed_optional` 在本地 MVP 中只会 graceful failure，不会让 workflow 崩溃。

关键规则：
- Reference Verification 只生成 candidate 和 `match_scores`，不会自动修改 `literature/literature_index.json`。
- Approval Workflow 默认 `apply_to_literature_index=false`，只写 `literature/reference_approvals.jsonl`。
- 只有人工 `decision=approved` 且显式 `apply_to_literature_index=true`，才允许写回 `literature_index.json`，并写入 `literature/metadata_history.jsonl` 与 `audit/audit_log.jsonl`。
- 正式 References 与正式 BibTeX entry 只允许来自 `metadata_status=verified`、`human_verified=true`、`reference_verification_status=approved` 的记录。
- `provenance/citation_grounding_report.json` 只表示本地 passage grounding strength，不证明科学事实、统计显著性、因果关系或 peer-review readiness。

v1.2 常用命令：
```bash
python scripts/run_demo.py
python scripts/validate_v12.py
```

- [v1.2 验收标准](docs/v1.2_acceptance_criteria.md)
- [v1.2 验收报告](docs/v1.2_acceptance_report.md)

## ResearchAgent v1.3 RAG Quality

v1.3 在 v1.2 基础上把 Literature RAG 从本地关键词检索升级为本地 `local_hybrid` 检索。它使用 keyword overlap、character n-gram similarity、metadata trust 和 chunk quality 组成 heuristic score，不接真实向量数据库、不调用外部 embedding 服务、不依赖外部网络。

新增输出：
- `literature/rag/chunk_quality_report.json`
- `literature/rag/retrieval_eval_set.json`
- `literature/rag/retrieval_eval_report.json`

新增 API：
- `GET /api/projects/{project_id}/literature/rag/quality`
- `GET /api/projects/{project_id}/literature/rag/eval-set`
- `POST /api/projects/{project_id}/literature/rag/evaluate`
- `GET /api/projects/{project_id}/literature/rag/evaluation`

v1.3 常用命令：
```bash
python scripts/run_demo.py
python scripts/validate_v13.py
```

RAG Quality 分数和 retrieval eval 指标只是本地检索质量启发式检查，不代表科学事实证明、真实 benchmark、production-ready 或 peer-review-ready。

- [v1.3 验收标准](docs/v1.3_acceptance_criteria.md)
- [v1.3 验收报告](docs/v1.3_acceptance_report.md)
## ResearchAgent v1.4 Statistical Assistant

ResearchAgent v1.4 adds a local Statistical Assistant for descriptive CSV analysis. It reads `analysis/result_summary.json` and `analysis/processed_data.csv`, then generates:

- `analysis/statistical_assistant_report.json`
- `analysis/statistical_assistant_notes.md`

The report includes dataset health checks, variable role suggestions, descriptive cards, association candidates, method suggestions, guardrails, and limitations. Statistical Assistant is descriptive only: it does not generate p-values, does not claim statistical significance, and does not perform causal inference.

v1.4 API:

- `GET /api/projects/{project_id}/analysis/statistical-assistant`
- `POST /api/projects/{project_id}/analysis/statistical-assistant/generate`

v1.4 commands:

```bash
python scripts/run_demo.py
python scripts/validate_v14.py
```

The frontend `Analysis` group contains `Statistical Assistant` and keeps mock fallback when the backend is unavailable. v1.4 remains a local MVP helper, not production-ready or peer-review-ready.

- [v1.4 Acceptance Criteria](docs/v1.4_acceptance_criteria.md)
- [v1.4 Acceptance Report](docs/v1.4_acceptance_report.md)

## ResearchAgent v1.5 Workspace Export

ResearchAgent v1.5 adds `Workspace Export` for local Word, LaTeX, and trust-report handoff artifacts. It generates:

- `exports/workspace/research_workspace_export.docx`
- `exports/workspace/research_workspace_export.tex`
- `exports/workspace/trust_report.md`
- `exports/workspace/trust_report.json`
- `exports/workspace/workspace_export_manifest.json`

The export uses only project-relative paths in its manifest and scans text artifacts for secret-like values and local absolute paths. The Word file and LaTeX source summarize existing local MVP artifacts; they do not fabricate DOI, references, p-values, significance, causal claims, OCR output, or scientific conclusions.

v1.5 API:

- `POST /api/projects/{project_id}/export/workspace`
- `GET /api/projects/{project_id}/export/workspace`

v1.5 commands:

```bash
python scripts/run_demo.py
python scripts/validate_v15.py
```

The frontend dashboard includes `Workspace Export` with mock fallback when the backend is unavailable. v1.5 remains a local MVP export workflow, not for production use, compliance evidence, or peer review submission.

- [v1.5 Acceptance Criteria](docs/v1.5_acceptance_criteria.md)
- [v1.5 Acceptance Report](docs/v1.5_acceptance_report.md)

## ResearchAgent v1.6 UX consolidation

ResearchAgent v1.6 adds a first-screen `Workspace Readiness` panel for the local dashboard. It consolidates runtime mode, workflow state, trust status, and export availability, then routes users to the existing Global Trust, RAG Quality, Statistical Assistant, and Workspace Export panels.

The v1.6 UX keeps the existing dashboard and drawer workflow. It does not add new backend routes, authentication, PostgreSQL, queues, deployment behavior, or scientific claims. The dashboard keeps mock fallback: the demo remains usable without an API key or external network access, and unavailable backend services are shown as local demo state.

v1.6 commands:

```bash
python scripts/validate_v16.py
```

- [v1.6 Acceptance Criteria](docs/v1.6_acceptance_criteria.md)
- [v1.6 Acceptance Report](docs/v1.6_acceptance_report.md)
