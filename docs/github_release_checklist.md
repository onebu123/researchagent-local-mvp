# GitHub Release Checklist

## 本地验证

- [ ] `python -m compileall services\api scripts`
- [ ] `python -m pytest services\api\tests`
- [ ] `python scripts\seed_demo.py`
- [ ] `python scripts\run_demo.py`
- [ ] `python scripts\validate_v01.py` 到 `python scripts\validate_v10.py`
- [ ] `python scripts\validate_v1.py`
- [ ] `cd apps\web && npm run typecheck`
- [ ] `cd apps\web && npm run build`
- [ ] `cd apps\web && npm audit`
- [ ] `cd apps\web && npx playwright test`

## 导出检查

- [ ] `python scripts/export_project_zip.py --project-id demo_project`
- [ ] zip 位于 `projects/demo_project/exports/`
- [ ] zip 内含 `README_EXPORT.md`
- [ ] zip 内含 manuscript、provenance、reviews、trust、analysis、figures、literature metadata、audit exports、run history
- [ ] zip 内不含 `.env*`、密钥、`node_modules`、`.runtime`、`.next`、Playwright 报告、缓存、绝对路径

## Git 检查

- [ ] 当前项目是独立 Git 仓库，或已确认要初始化独立仓库
- [ ] `.gitignore` 覆盖密钥、缓存、数据库、node_modules、构建产物、Playwright 产物、project exports
- [ ] `git status --short` 只包含本次 v1.0 目标文件
- [ ] 没有把 `projects/*/exports/` zip、`.env*`、SQLite 数据库、缓存或测试报告加入提交
- [ ] commit message 描述 v1.0 Local MVP release
- [ ] 如需 tag，使用 `v1.0.0-local-mvp`

## GitHub 上传

如果本机 `gh auth status` 已登录：

```bash
gh repo create researchagent-local-mvp --private --source . --remote origin --push
git tag v1.0.0-local-mvp
git push origin v1.0.0-local-mvp
```

如果未登录：

```bash
gh auth login
gh repo create researchagent-local-mvp --private --source . --remote origin --push
```

不要把 secret、`.env*`、导出 zip、数据库、缓存、测试报告上传到 GitHub。
