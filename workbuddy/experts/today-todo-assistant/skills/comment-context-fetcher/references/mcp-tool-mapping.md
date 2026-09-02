# MCP 工具映射

## 映射关系

| 需求 | MCP 工具 | 说明 |
|------|---------|------|
| 查询项目详情 | `get_project_detail` | `object_type = "project"` 时调用 |
| 查询项目最近进展列表 | `get_process_list` | `object_type = "project"` 时追加调用，固定参数 `index=1, size=5, platform_version=3, status=1, publish_status=-1`（最近 5 条进展；无进展则仅用项目详情） |
| 查询进展详情 | `get_process_detail` | `object_type = "process"` 时调用 |
| 查询进展所属项目详情 | `get_project_detail` | `object_type = "process"` 时追加调用，入参取评论自带 `project_id`（与 project 评论合并去重，单次 run 内同一项目仅拉一次） |

## 调用策略

> **缓存策略**：单次 run 内按 id 去重（同一项目/进展仅拉一次），去重后并发请求；**不做跨 run 磁盘缓存**——每次 run 都实时拉取。

### 1. 按 object_type 分组 + 去重

```javascript
const groups = {
  project: [],  // object_type = "project"
  process: []   // object_type = "process"
};

items.forEach(item => {
  if (groups[item.object_type]) {
    groups[item.object_type].push(item.object_id);
  }
});

// 同一 object_id 单次 run 内只保留一条
const uniqueProjectIds = [...new Set(groups.project)];
const uniqueProcessIds = [...new Set(groups.process)];
```

### 2. 并行批量调用

```javascript
// project 组：项目详情
const projectPromises = uniqueProjectIds.map(id =>
  mcp.call('get_project_detail', { project_no: id })
);

// project 组：最近 5 条进展（除 project_id 外参数固定）
const processListPromises = uniqueProjectIds.map(id =>
  mcp.call('get_process_list', {
    project_id: parseInt(id, 10),
    index: 1,
    size: 5,
    platform_version: 3,
    status: 1,
    publish_status: -1
  })
);

// process 组（object_id 为数字字符串，需转为 uint32）
const processPromises = uniqueProcessIds.map(id =>
  mcp.call('get_process_detail', { id: parseInt(id, 10) })
);

// process 所属项目：取 process 评论自带 project_id，与 project 组合并去重后并行拉取
const processProjectIds = [...new Set(
  items.filter(i => i.object_type === 'process').map(i => i.project_id)
)].filter(pid => !uniqueProjectIds.includes(pid));
const processProjectPromises = processProjectIds.map(pid =>
  mcp.call('get_project_detail', { project_no: pid })
);

// 并行调用（project详情 / project进展列表 / process / process所属项目 四类同时发起）
const [projectResults, processListResults, processResults, processProjectResults] = await Promise.all([
  Promise.all(projectPromises),
  Promise.all(processListPromises),
  Promise.all(processPromises),
  Promise.all(processProjectPromises)
]);
```

### 3. 组装结果

```javascript
const contexts = {};
// project 类型上下文 = 项目详情 + 最近5条进展列表（无进展时空数组）
// process 类型上下文 = 进展详情 + 所属项目详情（取评论自带 project_id 对应的项目详情结果，
// 项目详情结果按 project_id 汇总，project 组与 process 所属项目组共享同一次拉取结果）
```

## 缓存策略

- **单次 run 内按 id 去重**：同一 `object_id` 只拉取一次；同一项目 `project_id` 只拉取一次（project 评论与 process 所属项目合并去重）；同一项目的进展列表只拉取一次
- 去重 key: `object_type:object_id`（评论上下文）、`project:<project_id>`（项目详情，跨类型共享）、`process_list:<project_id>`（项目进展列表）
- **不做跨 run 磁盘缓存**：去重仅单次 run 内有效，每次 run 项目详情 / 进展列表 / 进展详情都实时拉取
- 留言列表（`get_org_upreplied_comments`）同样始终实时拉取不缓存

## 降级策略

| 场景 | 处理方式 |
|------|---------|
| MCP 调用失败 | `contexts[object_id] = { type, project_detail: null }`；若为 `get_process_list` 失败则该 project 上下文 `process_list: []`（项目详情仍有效则保留） |
| 项目/进展不存在 | `contexts[object_id] = { type, project_detail: null }` |
| 部分失败 | 成功的正常返回，失败的设为 `null` |
