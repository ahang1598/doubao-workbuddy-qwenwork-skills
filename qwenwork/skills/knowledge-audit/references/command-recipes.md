# 知识库审计 — DWS 命令手册

> 与 SKILL.md 的 Module A/B/C 对应。所有命令必须加 `--format json`。

---

## 1. 文档扫描（Module A · A1）

### 1.1 个人文档空间（范围选项 ①）

```bash
dws doc list --format json
```

返回根目录下所有节点，包含 `type=file`（文档）和 `type=folder`（文件夹）。

### 1.2 指定知识库或文件夹（范围选项 ②）

```bash
dws doc list --folder "{知识库首页URL或文件夹URL}" --page-size 50 --format json
```

### 1.3 关键词搜索（范围选项 ③）

```bash
dws doc search --keyword "{关键词}" --format json
```

注意：关键词搜索不涉及递归，直接返回匹配文档列表。

### 1.4 递归扫描子文件夹（范围 ①② 必须执行）

`doc list` 返回的每个节点包含 `type` 字段：
- `type=file` → 加入文档列表，进入 A2
- `type=folder` → 加入待遍历队列，继续 `doc list --folder`

```
递归策略（BFS 广度优先）:

初始: doc list (或 doc list --folder "{URL}") → 获取节点列表
  ↓
对每个 type=folder 的节点:
  → dws doc list --folder "{folderUrl}" --page-size 50 --format json
  → 返回的节点中再次区分 file/folder
  → folder 继续入队
  ↓
重复直到队列为空

分页: 若返回 nextPageToken，继续:
  → dws doc list --folder "{URL}" --page-token "{token}" --format json
```

防护措施：
- 文件夹递归深度上限：5 层（超过跳过并记录警告）
- 单文件夹翻页上限：10 次（即最多 500 个子项）
- 文档总数上限：2000 篇（超过停止遍历，使用已获取数据）

---

## 2. 元数据读取（Module A · A2）

```bash
dws doc info --node "{docUrl}" --format json
```

提取字段：
- `title`/`name` → 标题规范性评分 + 分类
- `type` → 文档类型（辅助分类）
- `creator`/`creatorName` → 归属判断
- `updatedAt`/`modifiedTime` → 新鲜度评分
- `parentFolder`（如有）→ 孤立度评分

---

## 3. 正文读取与摘要（Module A · A3，仅深度模式）

```bash
dws doc read --node "{docUrl}" --format json
```

提取 `markdown` 正文后，AI 生成 ≤ 100 字摘要，存入分析上下文。

摘要格式：`{文档标题} | {核心主题} | {文档类型判断} | {关键实体/数据}`

深度模式批量策略：
- ≤ 30 篇：逐篇读取 + 摘要
- 31-100 篇：分批处理，每批 10 篇
- > 100 篇：建议用户缩小范围或切换轻量模式

---

## 4. 创建分类目录（Module C · C1）

```bash
dws doc folder create --name "{分类名称}" --workspace "{知识库ID}" --format json
```

在已有文件夹下创建子目录：

```bash
dws doc folder create --name "{分类名称}" --folder "{父文件夹完整URL}" --format json
```

提取：`docUrl`（新目录 URL）

---

## 5. 创建索引文档（Module C · C2）

```bash
dws doc create --name "{知识库名称}审计报告与知识地图 {YYYY-MM}" --workspace "{知识库ID}" --format json
```

提取：`docUrl`（索引文档 URL）

---

## 6. 写入索引内容（Module C · C3）

```bash
dws doc update --node "{索引文档docUrl}" --content "{MARKDOWN内容}" --content-format markdown --mode append --format json
```

规则：
- 每块 ≤ 1500 字符，按章节分块追加
- 默认 `--mode append`，除非用户明确确认否则不用 overwrite
- 写入结构详见 [index-template.md](./index-template.md)
