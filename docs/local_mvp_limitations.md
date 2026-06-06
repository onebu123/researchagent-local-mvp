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

## Project Export 的边界

Project Export 是本地项目材料包，不是生产备份。

导出会排除 `.env*`、密钥、缓存、运行时目录、Playwright 结果和明显绝对路径内容。它仍然可能包含用户主动放入项目产物的研究内容，因此导出前应人工复核。
