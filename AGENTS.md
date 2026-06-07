## ResearchAgent v0.9 开发边界
- `python scripts/validate_v01.py` 到 `python scripts/validate_v09.py` 必须持续通过。
- Revision diff review 只能写入 `manuscript/revision_diffs/revision_diff_reviews.jsonl` 和 summary；不得修改 `manuscript/draft.md`、version、patch、merge、diff 或 revision diff 原文件。
- Metadata review action 只能写入 `literature/metadata_review_actions.jsonl` 和 summary；不得自动修改 `literature/literature_index.json`，不得把 placeholder/extracted 自动标记为 verified。
- PDF page review 只能记录人工页级状态；`needs_ocr` 不得触发真实 OCR，不得生成 OCR 文本，不得把低质量页当成可靠全文来源。
- Analysis timeline 只能基于已有 `runs/run_history.json` 和 `analysis/comparisons/*.json`；不得伪造 run_id、comparison、provenance、参数、hash、runtime、warnings 或 limitations。
- Audit filtered export 只能导出本地筛选报告；不得包含 secret、API key、内部绝对路径或堆栈；不得把 filtered export 宣称为生产级合规审计。
- 所有 v0.9 写入操作必须写 audit log，并保持 audit hash chain 可验证。
- 前端 v0.9 面板必须保留 mock fallback；后端不可用时 dashboard 仍需可渲染。
- 不得绕过 Claim Alignment、Reviewer sentence-level issue、patch_safety、Evidence Checklist 或 claim_id 稳定性。
- 不得伪造 DOI、作者、年份、期刊、页码、p 值、统计显著性、因果关系、真实实验结论或 verified references。
- v0.9 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 核验、真实 OCR、真实科研软件、真实仪器或真实查重。
# ResearchAgent 开发指南

## 项目目标

ResearchAgent 是一个可审计的科研论文草稿系统，不是论文代写器。系统目标是把项目资料、PDF 解析文本、文献 metadata、CSV 分析、analysis provenance、figure provenance、evidence claim、manuscript、claim alignment 和 reviewer issue 连接成可复核链路。

## 代码风格

- 回复、注释和文档使用中文；代码命名使用英文。
- Python 使用类型标注、Pydantic DTO、service 分层和 pathlib。
- TypeScript 开启 strict，不使用 `any` 逃避类型检查。
- 路由只做协议适配，业务逻辑放到 service、agent、tool 或 workflow。
- mock、demo、placeholder 内容必须明确标记。

## v0.3 冻结边界

开发 v0.3 之后的功能时必须保护：

- `python scripts/validate_v01.py` 必须继续通过。
- `python scripts/validate_v02.py` 必须继续通过。
- `python scripts/validate_v03.py` 必须继续通过。
- 不得破坏 `literature/literature_index.json`、`analysis/result_summary.json`、`analysis/analysis_provenance.json`、`figures/figure_provenance.json`、`provenance/evidence.json`、`provenance/claim_alignment.json`、`manuscript/draft.md`、`reviews/review_report.json` 的核心字段。
- 不得伪造 verified references。
- 不得伪造统计显著性、p 值、因果结论或真实实验结论。
- 不得跳过 evidence alignment。
- 不得把 mock 结果伪装成真实科研结论。

## 文件结构

- `apps/web`：Next.js dashboard。
- `services/api`：FastAPI 后端。
- `services/api/app/api`：REST 路由。
- `services/api/app/services`：项目、存储、工作流服务。
- `services/api/app/agents`：多 Agent 实现。
- `services/api/app/tools`：CSV、PDF、绘图、LLM、metadata、provenance 工具。
- `services/api/app/workflows`：ResearchState 和轻量 workflow。
- `projects`：本地项目文件存储。
- `scripts`：demo 与验证脚本。
- `docs`：验收标准、验收报告和冻结清单。

## 必跑验证

后端：

```bash
python -m compileall services\api scripts
python -m pytest services\api\tests
python scripts\seed_demo.py
python scripts\run_demo.py
python scripts\validate_v01.py
python scripts\validate_v02.py
python scripts\validate_v03.py
```

前端：

```bash
cd apps\web
npm run typecheck
npm run build
npm audit
npx playwright test
```

## Agent 开发规范

- 所有 Agent 继承 `BaseAgent`。
- Agent 输入和输出通过 `ResearchState` 或项目文件。
- Agent 输出文件必须注册到 state outputs，最终由 workflow service 注册到 SQLite。
- Results 只能来自 `analysis/result_summary.json`、`analysis/analysis_provenance.json` 和 `figures/figure_provenance.json`。
- Manuscript 的 Evidence Checklist 必须列出 `claim_id`，且 `claim_id` 必须存在于 `provenance/evidence.json`。
- Claim Alignment Agent 必须在 Manuscript Agent 之后、Refinement Agent 之前运行。
- Reviewer 必须读取 `claim_alignment.json`，并把 sentence-level 风险写入 `sentence_issues`。
- References 必须分为 `Placeholder literature records` 和 `Verified references`。
- Verified references 只能来自 `metadata_status=verified` 且 `human_verified=true` 的文献。

## Tool 开发规范

- 文件路径一律使用 pathlib。
- 读写项目文件必须限制在项目目录内。
- PDF 解析失败时不得删除原始 PDF，必须在 parsed metadata 中记录 `parse_status` 和 warnings。
- PDF metadata 必须保留 quality_score、quality_label、needs_manual_review。
- CSV 分析工具只做可复现描述性统计，不写不可验证结论。
- Analysis provenance 必须记录输入数据 hash、分析函数、生成文件、运行时版本和 limitation。
- 绘图工具必须输出 PNG、SVG 和 `figure_provenance.json`。
- `figure_provenance.json` 每条记录必须包含 `data_hash`，且 `is_ai_generated=false`。
- LLM client 默认 mock；真实 OpenAI-compatible 调用失败时必须 fallback 到 mock。

## API 开发规范

- 外部输入必须走 Pydantic 或显式校验。
- 上传文件限制后缀、大小和目标目录。
- 输出响应只返回相对路径，不泄露内部绝对路径、密钥或堆栈。
- 缺文件 API 返回清晰 404，不返回伪成功。
- 文献 PATCH 只能保存用户输入，不得自动生成 DOI、作者、年份或期刊。

## 前端开发规范

- 保持 v0.2 dashboard + drawer 模式，不做复杂 UI 重构。
- 后端不可用时必须保留 mock fallback。
- 新 panel 必须有清晰空态、加载态和类型定义。
- Literature Metadata Panel 只允许编辑 title、authors、year、doi、journal、metadata_status、human_verified。
- 不把前端 UI 当成服务端安全边界。

## 禁止事项

- 不伪造实验结果。
- 不伪造引用、DOI、作者、年份、期刊或页码。
- 不伪造 p 值、统计显著性或因果关系。
- 不把 AI 生成图冒充真实实验图。
- 不把 demo 数据当作真实实验数据。
- 不把 placeholder 文献自动变成 verified。
- 不绕过 claim alignment 和 evidence 检查。
- 不承诺绕过查重或 AI 检测。
- 不把用户上传文件名拼接成越界路径。
- 不在 v0.3 引入 Redis、Celery、PostgreSQL、LangGraph 强制依赖或公网部署。
## v0.4 冻结前新增开发边界

- `python scripts/validate_v01.py`、`python scripts/validate_v02.py`、`python scripts/validate_v03.py` 和 `python scripts/validate_v04.py` 必须继续通过。
- Reviewer sentence issue 的 `revision_diff` 只能提供保守修订建议，必须保留 `requires_human_approval=true`，不得自动修改 `manuscript/draft.md`。
- `reviews/revision_decisions.jsonl` 只记录 accepted/rejected 决策，`applied_to_manuscript` 必须保持 `false`。
- 文献 metadata PATCH 只能保存用户提交字段，并写入 `literature/metadata_history.jsonl`；不得自动生成 DOI、作者、年份、期刊或 verified 状态。
- PDF metadata 必须保留 v0.3 质量字段，并新增页级 `pages[]` 与 OCR not_configured 预留字段；v0.4 不执行 OCR。
- Analysis provenance 必须保留 input hash、runtime 和 limitations，并新增 parameters、script_version、random_seed、output_file_hashes。
- Audit log 和 run history 只能记录本地相对路径与摘要，不得记录 API key、secret 或内部绝对路径；它们不是权限系统。
- 前端继续使用 dashboard + drawer/panel 模式，后端不可用时必须保留 mock fallback。
# ResearchAgent v0.5 开发边界

- `python scripts/validate_v01.py`、`validate_v02.py`、`validate_v03.py`、`validate_v04.py`、`validate_v05.py` 必须继续通过。
- accepted revision decision 可以生成 manuscript patch，但 patch 不能自动覆盖 `manuscript/draft.md`。
- confirmed patch 只能生成 `manuscript/versions/manuscript_v*.md`，并写入 `manuscript/versions/version_history.json`。
- patch item 必须经过 `patch_safety.py` 检查；不得修改数字和单位，不得引入 DOI、p 值、统计显著性、因果结论或不存在的 `claim_id`。
- 所有 patch、confirm/reject、version 写操作必须写入 `audit/audit_log.jsonl`。
- audit log 必须保留 `prev_hash` 和 `entry_hash`；hash chain 只是本地完整性辅助，不是生产级不可篡改审计。
- 前端继续使用 dashboard + drawer/panel 模式，后端不可用时必须保留 mock fallback。
- v0.5 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 数据库、真实 OCR 或查重。
## ResearchAgent v0.6 开发边界

- `python scripts/validate_v01.py` 到 `python scripts/validate_v06.py` 必须继续通过。
- patch item edit 只能修改 `after` 和 `reason`，不得修改 `before`、`issue_id`、`decision_id`、`related_claim_id`、`section`、`paragraph_index`、`sentence_index`。
- patch item edit 和 safety-check 必须调用 `patch_safety.py`，unsafe item 只能标记为 `blocked` 或 `needs_revision`，不得被应用到 manuscript version。
- patch conflict check 必须输出本地 report，并写入 audit log。
- merge preview 只能输出 preview JSON/Markdown，不得覆盖 `manuscript/draft.md`，不得自动生成或覆盖 manuscript version。
- manuscript diff 只能读取 draft/version 并输出 diff，不得修改任何 manuscript 文件。
- issue resolution 只能基于 patch/version provenance 判断，不能假装语义层面已经解决。
- audit export 是本地完整性辅助报告，不是生产级不可篡改审计；不得记录 secret、API key 或内部绝对路径。
- 前端继续使用 dashboard + drawer/panel 模式，后端不可用时必须保留 mock fallback。
- v0.6 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 数据库、真实 OCR、真实科研软件、真实仪器或真实查重。
## ResearchAgent v0.7 开发边界

- `python scripts/validate_v01.py` 到 `python scripts/validate_v07.py` 必须持续通过。
- merge preview 只能在人工显式 confirm 后生成新 manuscript version；不得自动覆盖 `manuscript/draft.md`。
- merge-generated version 必须写入 `version_history.json`，并保留 `source_type="merge"`、`source_merge_id`、`source_patch_ids`、`source_decision_ids`、`source_issue_ids`。
- `version_lineage.json` 只能从本地 patch、merge、version、diff、issue-resolution provenance 推导，不得伪造不存在的关系。
- issue resolution human review 必须写入 `reviews/issue_resolution_reviews.jsonl`；自动 resolved/partial/unresolved 只能代表 provenance 关系，不得宣称语义问题已被系统证明解决。
- audit file manifest 只能记录相对路径、分类、大小和 SHA256；不得泄露本机绝对路径、API key、secret 或堆栈。
- 前端继续保持 dashboard + drawer/panel 模式；后端不可用时必须保留 mock fallback。
- v0.7 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 核验、真实 OCR、真实科研仪器或真实查重。

## ResearchAgent v0.8 开发边界

- `python scripts/validate_v01.py` 到 `python scripts/validate_v08.py` 必须持续通过。
- revision line diff 只能读取 manuscript draft/version 并输出 `manuscript/revision_diffs/*.json`；不得修改 `manuscript/draft.md`、已有 version 或 patch。
- metadata revert suggestion 只能生成撤销建议；不得自动修改 `literature/literature_index.json` 或把 verified 状态回写为 placeholder。
- metadata batch review 只能生成本地审阅报告；不得自动改变任何文献的 `metadata_status`、`human_verified`、DOI、作者、年份、期刊或页码。
- PDF quality report 只能报告页级质量、疑似扫描页和 OCR 未配置状态；不得伪装 OCR 已执行，也不得把低质量页面当作可靠全文来源。
- analysis compare 只能比较已存在的 provenance 文件；不得伪造运行参数、输入 hash、输出 hash、runtime、warnings 或 limitations。
- audit event classification 必须保留 hash chain 校验能力；新增 `event_category`、`risk_level`、`entity_type`、`entity_id` 不得被当作权限系统。
- run history diagnostics 只能记录失败诊断和建议恢复；不得引入队列或自动重试失败任务。
- 前端 v0.8 面板必须保留 mock fallback；真实后端不可用时 dashboard 仍需可渲染。
- 不得伪造统计显著性、p 值、因果结论、真实实验结论、DOI 或 verified reference。
- v0.8 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 核验、真实 OCR、真实科研软件、真实科研仪器或真实查重。
## ResearchAgent v1.1 开发边界

- `python scripts/validate_v11.py` 必须调用并保持 `python scripts/validate_v1.py` 通过；无 API key、无网络要求时也必须可运行。
- LLM client 默认 `LLM_MODE=mock`；live 只允许 OpenAI-compatible 调用，失败必须 fallback，不得泄露 API key、Authorization header、完整敏感 prompt 或本机绝对路径。
- Prompt 必须版本化存放于 `services/api/app/prompts/`；RAG、citation support、metadata lookup、BibTeX 产物必须记录 `prompt_version`。
- Literature RAG 只能使用本地 parsed literature 文本；回答必须绑定真实 `chunk_id` 和 `source_passages`，否则写 `unsupported_notes`。
- Metadata lookup 默认 `mock_fixture`，不得自动联网或回写 `literature/literature_index.json`；optional provider 结果仍需人工验证。
- BibTeX 正式条目只允许来自 `metadata_status=verified` 且 `human_verified=true` 的文献；不得伪造 DOI、作者、年份、期刊或页码。
- Citation support 只能给 `supported`、`partial`、`unsupported`、`needs_human_review` 状态；placeholder 文献不得升级为已验证支持。
- 前端必须保留 dashboard + drawer/panel 模式和 mock fallback，不把 UI 当安全边界。
- v1.1 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、强制 PaperQA2、真实 OCR、生产部署或 peer-review-ready 声明。

## ResearchAgent v0.10 开发边界

- `python scripts/validate_v01.py` 到 `python scripts/validate_v10.py` 必须持续通过。
- Evidence claim review 只能写入 `provenance/evidence_claim_reviews.jsonl` 和 summary；不得自动修改 `provenance/evidence.json` 或伪造 human verification。
- Trust summary/readiness report 只能作为本地 MVP 审计辅助；不得宣称 production-ready、compliance-ready、peer-review-ready 或生产安全边界。
- Reviewer closure 只能表示 sentence issue 与 revision diff human review 的 workflow closure；不得把它当成语义问题已自动解决的证明。
- Metadata revert preview 只能生成预览，必须保持 `applied=false` 和 `literature_index_modified=false`；不得自动修改 `literature/literature_index.json`。
- PDF page text preview 只能使用已有 parsed text / metadata；不得执行 OCR 或生成 OCR 文本。
- Enhanced analysis timeline 只能基于已有 run history、analysis provenance 和 comparison 文件；不得伪造 run、comparison、hash 或 failure diagnostics。
- Failure fixture 必须幂等，不得重复追加 `run_failure_fixture_001`。
- v0.10 前端必须保留 dashboard + drawer/panel 模式和 mock fallback。
- v0.10 不引入登录、多租户、PostgreSQL、Redis、Celery、LangGraph、公网部署、真实 DOI 验证、真实 OCR、真实科研软件/仪器或查重。

## ResearchAgent v1.2 开发边界
- `python scripts/validate_v12.py` 必须保持可运行，并通过 v1.1 validation 保护既有能力。
- Reference Verification 只生成候选、`match_scores`、summary 和 audit；不得自动修改 `literature/literature_index.json`，不得自动写 DOI、作者、年份、期刊、页码或 verified 状态。
- Approval Workflow 默认 `apply_to_literature_index=false`，只能记录人工 decision；只有 `decision=approved` 且显式 `apply_to_literature_index=true` 时，才允许写回索引并记录 `literature/metadata_history.jsonl` 与 `audit/audit_log.jsonl`。
- 正式 manuscript References 与正式 BibTeX entry 只允许来自 `metadata_status=verified`、`human_verified=true`、`reference_verification_status=approved` 的记录。
- rejected、needs_manual_check、candidate、placeholder 文献不得进入正式 References 或正式 BibTeX entry。
- Citation Grounding 只能基于本地 RAG/source passages 输出 `provenance/citation_grounding_report.json`；`strong` 也不是科学事实证明、统计显著性证明、因果证明或 peer-review-ready 声明。
- optional reference providers 在无网络或未配置时必须 graceful failure，不得成为 demo、test 或 validation 的硬依赖。
- 前端必须保留 mock fallback；`ReferenceVerificationPanel`、`ReferenceApprovalPanel`、`CitationGroundingPanel`、`VerifiedReferencesPanel` 不得把 candidate 显示成 verified。
