---
name: cnb-api
description: CNB 平台交互命令，支持代码仓库、Issue、PR、CI、制品库读写等操作。
---

# cnb-api

## 快捷命令

issues:
- `cnb issues get` — 获取详情
- `cnb issues list-comments` — 获取评论列表
- `cnb issues comment --body 内容` — 评论
- `cnb issues close` — 关闭
- `cnb issues open` — 打开
- `cnb issues list-labels` — 查看标签
- `cnb issues add-labels --labels bug --labels feature` — 添加标签
- `cnb issues list-assignees` — 查看处理人
- `cnb issues add-assignees --assignees username` — 添加处理人
- `cnb issues get-imgs --img-path 图片路径` — 获取 issue 图片
- `cnb issues get-files --file-path 附件路径` — 获取 issue 附件

pulls:
- `cnb pulls get` — 获取详情
- `cnb pulls list-files` — 获取文件变更
- `cnb pulls list-commits` — 获取提交记录
- `cnb pulls list-comments` — 获取评论列表
- `cnb pulls comment --body 内容` — 评论
- `cnb pulls list-labels` — 查看标签
- `cnb pulls add-labels --labels ready --labels approved` — 添加标签
- `cnb pulls check-status` — 查看 CI 状态
- `cnb pulls list-reviews` — 查看评审列表
- `cnb pulls list-assignees` — 查看处理人
- `cnb pulls get-ci-logs --sn 构建号（可选）` — 获取 CI 失败日志
- `cnb pulls get-ci-timing --sn 构建号（可选）` — 分析 CI 耗时瓶颈
- `cnb pulls get-imgs --img-path 图片路径` — 获取 PR 图片
- `cnb pulls get-files --file-path 附件路径` — 获取 PR 附件

skills:
- `cnb skills list --json -g -p -a agent` — 列出本地 skills

注意事项：

- **参数自动识别**：Issue/PR 编号自动从环境变量识别，无需额外传递。
- **默认仅需摘要**：默认精简输出，加 `--verbose` 输出完整数据。
- **多行文本传参**：bash 参数为多行文本时用单引号，降低命令注入风险。
- **适用范围**：快捷命令仅限当前仓库的当前 Issue/PR，跨仓库或跨编号请参考 `更多 API`。
- **提及与召唤**：评论中直接 @npc 会召唤 npc；仅提及不召唤时，用反引号包裹 `@npc`。

## PR 相关规范

> 本节 PR 规范为默认约定，若项目另有规定，以项目规定为准。

### 标题

- **一行表达**：采用语义化提交格式。
- **只保留核心问题**：标题要简洁、可读、语义清晰。
- **可读性**：影响可读性的信息禁止写入标题。
- **禁止括号**：标题禁止出现括号，补充说明写描述区。
- **禁止分支名**：标题禁止出现分支名（如 `hotfix/1.27.x`），目标分支由 PR base 表达。

### 描述

- **关联引用**：需包含 `Ref: #<ISSUE_ID>`。
- **关联信息**：关联信息和补充说明应该写进描述区，比如 `Ref #xxx`、`cherry-pick #xxx`、版本号、日期、作者等。
- **cherry-pick**：目标版本写入 body 末尾。

### 提交流程

- **提交后立即结束**：创建/推送 PR 后马上结束，不做其他操作。
- **禁止轮询 CI 与评审**：不等待 CI 与评审状态；失败会自动唤起 NPC。
- **禁止合并/关闭**：AI 不执行合并/关闭操作，合并交由人工完成。

## 常用链接

生成链接时遵循以下结构：
- Issue: `<host>/<slug>/-/issues/<number>`
- PR: `<host>/<slug>/-/pulls/<number>`

## 更多 API

1. `cnb --help` 查看所有模块
2. `cnb <module> --help` 查看模块下的工具列表
3. `cnb <module> <tool> --help` 查看工具参数
