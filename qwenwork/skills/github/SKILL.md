---
name: github
description: 通过 `gh` CLI 与 GitHub 交互。支持 `gh issue`、`gh pr`、`gh run`、`gh api` 等命令，用于管理 Issue、PR、CI 运行和高级查询。不要在非 GitHub 场景（如 GitLab、Bitbucket、纯 git 操作）时触发。
install_source: official
install_method: download
skill_id: official_QA2JBeZa
enabled_at: 1791893738311
version: 1.0.0
name_zh: github工具
---

## 环境前置：gh CLI 依赖

本技能所有命令依赖 `gh`（GitHub 官方命令行工具）。执行任何 `gh` 命令前，必须先运行存在性检查：

```bash
command -v gh >/dev/null 2>&1 && echo "gh 已就绪" || echo "gh 未安装"
```

若 `gh` 未安装，提示用户安装并完成认证后再继续，不要强行执行命令（会报 `command not found`）：

- macOS：`brew install gh`
- Windows：`winget install GitHub.cli`
- 其他平台及源码安装：https://cli.github.com/

安装后需运行 `gh auth login` 完成 GitHub 账号认证。

## GitHub 技能

通过 `gh` CLI 与 GitHub 交互。不在 git 目录下时，需使用 `--repo owner/repo` 指定仓库，也可以直接使用 URL。

## Pull Requests

查看 PR 的 CI 状态：
```bash
gh pr checks 55 --repo owner/repo
```

列出最近的工作流运行记录：
```bash
gh run list --repo owner/repo --limit 10
```

查看某次运行详情及失败步骤：
```bash
gh run view <run-id> --repo owner/repo
```

仅查看失败步骤的日志：
```bash
gh run view <run-id> --repo owner/repo --log-failed
```

## 高级 API 查询

`gh api` 命令适用于获取其他子命令无法直接获取的数据。

获取 PR 的指定字段：
```bash
gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'
```

## JSON 格式输出

大多数命令支持 `--json` 参数输出结构化数据，可配合 `--jq` 进行过滤：

```bash
gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'
```
