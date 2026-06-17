# ResearchAgent 维护者运行手册

本文档面向维护者与发布执行者，覆盖 v3.0.0-rc1 之后的本地验证、外部 provider 使用、人工复核和禁止声明。它不是发布批准书，也不是同行评审证明。

## 发布前检查

每个发布候选或面向 GitHub 的 PR 至少记录以下命令结果：

```bash
python -m compileall services/api scripts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest services/api/tests -q
python scripts/validate_v38.py
python scripts/check_secrets_static.py
cd apps/web && npm run typecheck
cd apps/web && npm run build
cd apps/web && npx playwright test --project=chromium
```

如果命令失败，可以继续保留 draft PR，但 PR 描述必须写明失败命令、失败原因、是否为继承问题，以及当前 `git status --short` 是否干净。不得把失败 validator、失败 CI 或 dirty worktree 描述成 release-ready。

## 外部 provider 使用

Reference verification provider 必须默认使用 mock/disabled/offline-safe 路径。`crossref_optional`、`semantic_scholar_optional`、`openalex_optional`、`arxiv_optional` 等外部元数据 provider 只能生成候选核验结果：

- CI 不依赖 live network。
- provider 失败必须 graceful fallback，记录 warning。
- 候选结果只进入 review flow。
- 人工批准前，不自动写入 `literature_index.json`。
- 不得凭 provider 候选伪造 DOI、正式引用或 verified reference。

## DOCX 与导出物

Paper DOCX export 是草稿交付物，仅用于人工审阅和维护者检查。它不进入 evidence trust package 作为 citation proof。

导出时必须确认：

- DOCX 可由常规 Word 工具读取。
- DOCX 包含 AI 草稿与 human-review caveat。
- DOCX 与 manifest 不包含 secrets、本机绝对路径或本地数据库路径。
- export manifest 记录 DOCX 与 source markdown 的 sha256。
- manifest 明确 `is_draft_artifact: true`、`citation_proof: false`。

## 人工复核点

以下项目必须保留人工复核，不得由自动流程绕过：

- generated-code proposal 的 source hash、静态扫描、沙箱策略与执行结果。
- experiment tree 的 best-node 选择、rerun 结果、revision patches。
- citation binding 的 unbound、weak binding、source-passage-only 句子。
- reference verification 候选元数据与正式引用批准。
- LaTeX/PDF compile warning、fallback preview PDF、DOCX 草稿。
- release package 中的 source/evidence manifest、secret scan、排除列表。

## 禁止声明

维护者、PR 描述、README 和 release notes 不得声称系统已经完成：

- peer review
- citation guarantee
- scientific proof
- publication readiness
- formal acceptance or validation by an external venue

可以描述为：local draft artifact、human-review queue item、source-passage binding、candidate metadata verification、release-readiness smoke check。

## 包与仓库卫生

不得提交或打包以下本地/运行时内容：

- `.env*`
- `node_modules`
- `.next`
- `dist`
- `projects`
- `reports`
- 本地数据库、缓存、coverage、测试报告
- 上传的 zip、patch、archive contents txt
- secrets、API key、token、private key

source/evidence package 必须继续使用项目相对路径和 manifest sha256。任何失败或排除异常必须写入 PR 描述。
