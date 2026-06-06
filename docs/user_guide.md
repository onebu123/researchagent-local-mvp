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

## 常用命令

```bash
python scripts/start_local_dev.py
python scripts/seed_demo.py
python scripts/run_demo.py
python scripts/export_project_zip.py --project-id demo_project
python scripts/validate_v1.py
```
