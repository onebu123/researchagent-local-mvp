# Demo 演示流程

## 1. 准备 demo

```bash
python scripts/reset_demo.py --yes
```

该命令只重置 `projects/demo_project`。

## 2. 启动服务

后端：

```bash
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3100
```

打开 `http://127.0.0.1:3100`。

## 3. 演示主路径

1. 查看首页 `Local MVP Overview`。
2. 点击 `Global Trust Dashboard`，查看 trust scores、blocking issues、failed run diagnostics。
3. 点击 `Release Readiness`，查看 local MVP checks 和 production gaps。
4. 点击 `Project Export`，生成本地 zip。
5. 点击 `Validate Local MVP`，页面会提示本地命令：`python scripts/validate_v1.py`。

## 4. 命令行导出

```bash
python scripts/export_project_zip.py --project-id demo_project
```

成功后会输出类似：

```text
Project export created: exports/researchagent_demo_project_local_mvp_export_YYYYMMDDTHHMMSSZ.zip
```

## 5. 验收

```bash
python scripts/validate_v1.py
```

通过时输出：

```text
ResearchAgent v1.0 Local MVP validation passed.
```
