# Local MVP 限制

ResearchAgent v1.0 是本地 MVP，不是生产系统。

## 明确不支持

- 不支持登录、鉴权、角色、权限、多租户。
- 不支持 PostgreSQL、Redis、Celery、LangGraph 或生产任务队列。
- 不支持公网部署、生产监控、告警、备份、恢复、迁移。
- 不支持真实 DOI、作者、期刊、页码、引用数据库联网核验。
- 不执行真实 OCR，不生成 OCR 文本。
- 不执行查重、AI 检测、统计显著性验证、因果推断或科学事实校验。
- 不连接真实科研仪器、实验平台或外部科研软件。
- 不提供合规认证、生产级防篡改审计或同行评审证明。

## Trust 与 Readiness 的边界

Global Trust Dashboard 汇总的是本地 workflow 产物和人工 review 记录。它只能帮助定位未闭环项，不能证明论文结论真实。

Release Readiness 只判断 local MVP 演示与导出是否准备好。它不能代表 production-ready、compliance-ready 或 peer-review-ready。

## v1.1 Literature Intelligence 的边界

- `LLM_MODE=mock` 是默认模式；live 仅表示本地配置了 OpenAI-compatible provider，不代表输出已验证。
- LLM call log 只记录摘要、hash、token/cost 占位、状态和错误类别；不得作为完整 prompt 存档。
- Literature RAG 只使用本地 parsed literature 文本；不会联网检索、不会真实 OCR、不会强制 PaperQA2。
- RAG answer 必须绑定真实 `source_passages`；没有本地支持时只能输出 `unsupported_notes`。
- Metadata lookup 默认 `mock_fixture`；optional provider 结果仍是候选，不会自动变成 verified reference。
- BibTeX 正式条目只来自 `metadata_status=verified` 且 `human_verified=true` 的记录。
- Citation Support 是本地文本支持检查，不证明科学真实性、统计显著性、因果关系或同行评审通过。

## Project Export 的边界

Project Export 是本地项目材料包，不是生产备份。

导出会排除 `.env*`、密钥、缓存、运行时目录、Playwright 结果和明显绝对路径内容。它仍然可能包含用户主动放入项目产物的研究内容，因此导出前应人工复核。

## v1.2 Reference Verification 的边界

- Reference Verification 不连接真实 DOI 数据库；默认只使用 `mock_fixture`。
- optional providers 只做可选候选来源，未配置或无网络时必须 graceful failure。
- candidate 不等于 verified reference；系统不得自动把 candidate 写入 `literature_index.json`。
- `apply_to_literature_index=true` 必须由人工显式触发，且只允许 `decision=approved`。
- `citation_grounding_report.json` 只表示本地 passage grounding strength，不证明科学事实、统计显著性、因果关系、同行评审通过或生产可用。
- 正式 References 与正式 BibTeX entry 只来自 `reference_verification_status=approved`、`metadata_status=verified`、`human_verified=true` 的记录。

## v1.3 RAG Quality 的边界

- `local_hybrid` 是本地启发式检索，不是真实向量数据库、embedding 服务或外部检索平台。
- `chunk_quality_report.json` 只提示 chunk 长度、token、lexical diversity 和 metadata trust 风险，不评价论文质量。
- `retrieval_eval_report.json` 使用本地 deterministic smoke cases，不是 benchmark-grade eval。
- hit@k、MRR、quality score 和 score breakdown 不证明科学事实、引用真实性、统计显著性、因果关系、production-ready 或 peer-review-ready。
- Placeholder metadata 会降低 retrieval trust，但不会因此自动进入 verified reference、正式 BibTeX 或正式 References。
## v1.4 Statistical Assistant 的边界

- Statistical Assistant 只做本地 descriptive CSV helper，不是推断统计系统。
- `statistical_assistant_report.json` 里的 role suggestions、association candidates 和 method suggestions 都需要人工领域复核。
- v1.4 does not generate p-values, does not claim statistical significance, and does not perform causal inference.
- v1.4 不把 demo data 当真实实验数据，不自动改写 manuscript，也不声明 production-ready、compliance-ready 或 peer-review-ready。
- `analysis/statistical_assistant_report.json` 和 `analysis/statistical_assistant_notes.md` 只包含项目相对路径，不应包含 API key、secret 或本机绝对路径。

## ResearchAgent v1.5 Workspace Export 的边界

- `Workspace Export` 只打包并总结 local MVP 的既有本地产物，不是备份、发布包、合规档案或投稿证明。
- `research_workspace_export.docx`、`research_workspace_export.tex`、`trust_report.json`、`trust_report.md` 和 `workspace_export_manifest.json` 只能使用项目相对路径。
- `research_workspace_export.tex` 只是 LaTeX source；v1.5 不执行完整 LaTeX 编译。
- `trust_report.json` 只描述本地 workflow evidence、source coverage、audit hash chain 和 caveats，不证明科学事实、统计显著性、因果关系、合规状态或审稿状态。
- 导出逻辑不得记录 API key、secret、完整 prompt、stack trace、环境文件内容或本机绝对路径。
- 导出逻辑不得伪造 DOI、作者、年份、期刊、引用、p-values、significance、causal claims、OCR output 或真实实验结论。
- Candidate 和 placeholder references 不得因为出现在导出文件中而变成 verified references 或正式 BibTeX/References。
