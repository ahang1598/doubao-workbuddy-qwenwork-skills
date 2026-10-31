# Base 公开模板命令

模板中心是独立公开 Base 模板库；查询返回模板，`+base-copy` 复制为新 Base。边界与顺序见 [Base 模板流程](../scenes/base.md#公开模板检索与创建)。

## 适用范围与权限

模板中心**不能**用 `drive +search` 找到，`drive +search` 只搜用户可访问的云空间对象。三个查询命令都只读，默认 `--as user`，需 `base:template:read`，不依赖目标 Base 权限。

## 查询命令与分页

|命令|用途|
|---|---|
|`+template-categories`|列出全部公开分类|
|`+template-list`|列出指定分类；不传分类则返回“推荐”类目|
|`+template-search`|按业务关键词搜索|

### 调用参数与示例

`+template-list --category-key <key>`：`key` 必须取自 `categories[].key`，不得自造。`+template-search --keyword "<词>"`：空关键词会被拒绝。

```bash
lark-cli base +template-categories --as user
lark-cli base +template-list --category-key template_center_tab_ai --limit 10 --as user
lark-cli base +template-search --keyword "项目管理" --limit 10 --as user
lark-cli base +template-search --keyword "AI" --limit 10 --offset "<上一页 offset>" --as user
```

### 翻页

`+template-list`、`+template-search` 用游标分页。`--limit` 默认 10、范围 1-100；`--page-size` 为别名。首次不得传 `--offset`，后续原样传前次 `data.offset`；它是不透明游标，不得解析或拼造。

`has_more=true` 表示有下页；`has_more=false` 或 `offset=""` 表示结束。

## 复制参数与能力边界

`templates[].token` 传给 `+base-copy --base-token`；`templates[].link` 只供预览，不得替代 token。模板 token 不得用于 `+base-get` 等用户 Base 命令。

链接含 `/app/` 即 BaseApp/应用模板，只能预览，不能用 `+base-copy` 创建；当前 CLI 只复制 Base 模板。

```bash
lark-cli base +base-copy --base-token "<模板 token>" --name "<新 Base 名>" --as user
```

`--name` 指定新 Base 名；省略则沿用模板名。内容范围参数、返回及部分成功处理见 [Base 复制协议](base-commands.md#复制-base)。

## 返回数据

### TemplateCategory（分类对象）

`+template-categories` 返回 `categories[]`：

|字段|类型|含义|
|---|---|---|
|`key`|string|分类唯一标识；用于 `--category-key`|
|`name`|string|分类展示名|

### Template（模板对象）

`+template-list`/`+template-search` 返回 `templates[]` 及分页字段：

|字段|类型|含义|
|---|---|---|
|`token`|string|Base token、唯一标识；用于复制|
|`name`|string|模板名|
|`introduction`|string|用途、内容结构、适用方向介绍|
|`scenarios`|string[]|适用场景|
|`developer`|string|模板开发者|
|`link`|string|预览链接|
|`created_at`/`updated_at`|string|创建/更新时间|
|`has_more`|boolean|是否有下页|
|`offset`|string|下页游标；无更多时为空字符串|

模板唯一标识必须称 `token`，不得改称 `id` 或 `key`；`key` 是分类标识（`category_key`）。

### 响应示例

```json
{
  "code": 0,
  "data": {
    "has_more": true,
    "offset": "1",
    "templates": [{
      "created_at": "", "developer": "",
      "introduction": "", "link": "https://example.com/base/<template_token>",
      "name": "品牌调研问卷", "scenarios": ["运营管理", "市场营销"],
      "token": "<template_token>", "updated_at": ""
    }]
  },
  "msg": ""
}
```
