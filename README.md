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

## 文档

- [用户指南](docs/user_guide.md)
- [Demo 演示流程](docs/demo_walkthrough.md)
- [Local MVP 限制](docs/local_mvp_limitations.md)
- [GitHub 发布检查清单](docs/github_release_checklist.md)
- [v1.0 验收报告](docs/v1.0_acceptance_report.md)
- [GitHub 上传状态](docs/github_upload_status.md)
