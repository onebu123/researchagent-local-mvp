# GitHub 上传状态

## 当前事实

- `gh --version`：已安装 GitHub CLI 2.92.0。
- `gh auth status`：已登录 GitHub 账号 `onebu123`，权限包含 `repo` 和 `workflow`。
- `D:\codex\学术agent\research-agent` 已初始化为独立 Git 仓库。
- 私有 GitHub 仓库已创建：`https://github.com/onebu123/researchagent-local-mvp`
- release 提交：`release: ResearchAgent v1.0 local MVP`
- release tag：`v1.0.0-local-mvp`
- `main` 分支和 `v1.0.0-local-mvp` tag 已推送到 GitHub。

## 上传门禁

- `.gitignore` 已忽略 `.env*`、数据库、缓存、构建产物、Playwright 产物、`node_modules` 和 `projects/` 运行时目录。
- 暂存和提交范围不包含 `projects/*/exports/` zip、SQLite 数据库、缓存、测试报告或本地密钥。
- 仓库类型为 private。

## 验证结果

上传前已通过 `python scripts/validate_v1.py`，输出 `ResearchAgent v1.0 Local MVP validation passed.`。
