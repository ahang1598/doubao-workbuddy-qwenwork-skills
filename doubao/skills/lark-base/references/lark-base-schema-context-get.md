# +schema-context-get：结构上下文

本参考只描述 Context 命令的调用与返回契约，不改变当前任务的分析口径、授权或回退边界。

**权限**：需要 `base:table:read`。参数细节以当前命令 `--help` 为准。

先按主 Skill 解析出可信 `base_token`，再获取结构上下文；未知相关表时不传 `--table-id`，从 Context 选表，已知相关表时重复传入以缩小结构范围：

```bash
# --table-id 可重复，最多 10 个；多表 Base 把相关表都传上
lark-cli base +schema-context-get --base-token <base_token> --language zh --table-id <tbl_a> --table-id <tbl_b>
```

| 参数 | 含义 |
| --- | --- |
| `--base-token` | Base 的 token，用 `+url-resolve` 从链接解析；一次只查一个 Base |
| `--table-id` | 可选，可重复，最多 10 个；只取这些表的 DDL，不传则取整个 Base |
| `--language` | `zh` / `en` / `ja`，DDL 注释和报错文案的语言 |

- 读取 JSON envelope 的 `data.content`：每张表一段 DDL，列的含义看 COMMENT，照着写 SQL；带视图 / 仪表盘段时，里面的 SQL 片段可以直接复用。表名、字段名只用 DDL 里出现的，一律双引号（`"订单"."记录 ID"`），不凭用户的简称或字段先验猜测。
- 结合 `PRIMARY KEY`、`UNIQUE`、重复值注释和表的业务粒度，区分记录键、业务实体键与展示属性。记录 ID 唯一只说明记录不同，不保证属于不同业务实体（如同一实体的多期快照）；已确认的实体键不同，即使名称相同也不合并。名称或少量样例不能证明实体身份，未声明 `UNIQUE` 也不等于已证明有重复；名称列没有重复提示也不等于名称唯一。
- 同一任务中，目标 Base、身份与结构未变且相关表字段已完整覆盖时，可以复用有效 Context。新增数据源、新建表或字段后必须重取，否则新字段不会出现。
- Context 截断时，先用 `+table-list` / `+field-list` 定位候选表，再重复传入明确的 `--table-id` 重取；筛选表必须覆盖问题所需的数据源和关联表，不因截断静默漏表。
- Context 的样例只用于理解字段，不代表完整数据或完整值域。需要确认状态取值、空值或关联覆盖时，用后续只读 SQL 查询补证据。
