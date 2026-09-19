# DAM 素材管理

## 先发现，再操作

任何资源库范围内的查询或写入都先运行：

```bash
gd-cli org current
gd-cli dam repository list --json
```

只使用返回的 `repositories[].repository_id`。团队资源库的 `type` 为 `team`，企业资源库的 `type` 为 `enterprise`；不要使用名称、前端 URL、团队实体 ID 或历史值猜 ID。资源库不做 switch，`org switch` 只切换组织。

需要文件夹或标签 ID 时继续发现：

```bash
gd-cli dam folder list --repository-id <id> --json
gd-cli dam tag list --repository-id <id> --json
```

文件夹可用 `--parent-id`、`--query`、`--page` 和 `--page-size`；标签可用 `--query`。根文件夹 ID 为 `0`，涉及目标位置时必须显式传 `--target-folder-id 0`，不要把缺省值理解为根目录。

## 查询与下载

```bash
gd-cli dam list --repository-id <id> --json
gd-cli dam search <query> --repository-id <id> --json
gd-cli dam get <asset-id> --json
gd-cli dam download <asset-id> --repository-id <id> --output-dir ./downloads --json
```

跨资源库查询只在用户明确要求时使用 `--all-repositories`。列表或搜索按需增加文件夹、类型、格式、标签、数量和游标筛选。下载只支持一个素材，不支持文件夹下载，也不会覆盖已存在的同名文件。

## 单条目写入

```bash
gd-cli dam upload ./asset.png --repository-id <id> --folder-id <folder-id> --tag-ids <tag-id> --json
gd-cli dam rename <entry-id> --kind asset --title <new-title> --repository-id <id> --json
gd-cli dam copy <entry-id> --kind asset --repository-id <source-id> --target-repository-id <target-id> --target-folder-id <folder-id> --json
gd-cli dam move <entry-id> --kind asset --repository-id <source-id> --target-repository-id <target-id> --target-folder-id <folder-id> --json
gd-cli dam delete <asset-id> --repository-id <id>
```

- `rename`、`move`、`copy` 的 `--kind` 只能是 `asset` 或 `folder`。
- 一次只处理一个素材或文件夹；不拆分或模拟批量操作。
- 上传受保护路径时，只有用户明确允许才加 `--allow-sensitive-path`；需要等待分析完成时加 `--wait-analysis`。
- 复制结果可能没有 `copied_entry_id`，这不表示失败；查询目标文件夹或目标资源库发现新副本，不要猜测新 ID，也不要再次提交 copy。
- 移动、复制或重命名若返回“已提交但未确认”，先查询目标位置并报告诊断 ID，不要立即重复提交。
- 删除默认移入回收站；只有用户明确要求永久删除时才加 `--permanent`。
- 回收站列表和恢复暂不可用，不要尝试不存在的 `dam recycle` 命令。

写操作前确认资源库、条目 ID、类型和目标位置。优先从本轮 JSON 输出取得 ID，不从本地登录状态或旧输出替用户猜测。
