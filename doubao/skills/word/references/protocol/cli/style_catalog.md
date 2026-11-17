---
keyword: style_catalog
---

**功能**：样式 identity、linked 关系、定义、继承和 builtin 来源查询

# 读取 Canvas 样式定义

需要写入时再查询 `local-update`。样式 identity、关系和 fingerprint 只能来自当前 CLI 的结构化读取结果，不得从 DocxXML 标签名、显示名称或历史结果猜测。

样式读写的结果在 `data.command_result`，返回对象字段而非正文 XML。

## 按目标读取

可以直接查任务用到的样式。

- 已知 style ID 时直接查询 `style_catalog --style-ids`，按需选 `definition` 或 `computed`。
- 从正文定位时，对目标范围使用可导出 block ID 的 detail 和 `--export-style-context refs`，从 `data.command_result.style_context` 取得 bindings、referenced styles 和 `styles_fingerprint`；layout 不支持此选项。
- 修改样式定义时读取 `style_usage`，按其规则查询；返回的 `target_style` 已含定义和 computed 信息，无需重复查同一目标的 catalog。设置或清除样式绑定时读取 `block_styles`，按其规则取得 guard，仅 set 另需目标样式的 catalog computed。

写入用的 ID 和 `expected_*_fingerprint` 来自同一文档版本。写入命令需传顶层 `--revision-id`，优先传读取结果中的版本，也可按 `local-update` 的规则传 `-1`。

### linked 样式与 builtin identity

catalog 的 identity/type/origin、关系及 computed/effective 是选择样式与 guard 的依据。linked 仍分别使用 paragraph/character 类型，应用时显式选择查询返回的对应侧 ID，不按名称推断。`origin=builtin_fallback` 不是已有文档定义，不能用于 `style_update`；有限 `style_apply materialize_builtin=true` 只按 `style_apply` 的普通模式集合执行，禁止覆盖已有定义。`origin=unresolved` 或未知 ID 不得应用。

结构化响应的 `property_schema` 用于核对当前属性能力：W0 `text.emphasis-mark` 为 `docxxml-attributes-v8` 的五值属性；definition、computed、effective 与来源分开检查，不能从版本名或 XML 缺席推断支持/关闭。

### 查询参数

三个 scope 的结构化结果位于 `data.command_result`，使用以下样式专属参数，不混用普通 XML 的 `--detail` 或 export 参数：

| scope | 参数与取值 |
|---|---|
| `style_catalog` | `--style-detail summary\|definition\|computed`，默认 summary；`--style-types paragraph\|character\|table\|numbering` 和 `--style-ids` 支持逗号分隔或重复参数，不筛选时省略；`--cursor`、`--limit`，limit 默认 100、最大 500 |

```bash
lark-cli docs +local-fetch --doc "<token>" \
  --scope style_catalog --style-ids "<style_id>" --style-detail computed
```
