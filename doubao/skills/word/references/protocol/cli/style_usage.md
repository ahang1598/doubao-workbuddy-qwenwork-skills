---
keyword: style_usage
---

**功能**：样式引用点与继承影响查询

# 查找样式用在哪里

需要写入时，通用参数见 `local-update`。样式 ID、关系和指纹取自当前 CLI 的结构化读取结果。

样式读写的结果在 `data.command_result`，返回对象字段而非正文 XML。

## 按目标读取

修改样式定义前，用 `style_usage --include-descendants=true` 读取完整影响范围。`target_style` 已含目标定义和计算结果，同时会返回三类指纹。已有这些信息就可以准备样式更新。

分页时将 `data.command_result.next_cursor` 原样传给下一次 `--cursor`，保持查询条件不变，读至 `truncated=false`。`style_update.expected_usage_fingerprint` 来自同一文档版本、`--include-descendants=true` 的完整影响集合。默认查询、单页结果和客户端自算的 hash 都不能替代它。

写入用的 ID 和 `expected_*_fingerprint` 来自同一文档版本。写入命令需传顶层 `--revision-id`，优先传读取结果中的版本，也可按 `local-update` 的规则传 `-1`。

### 查询参数

三个 scope 的结构化结果位于 `data.command_result`，使用以下样式专属参数，不混用普通 XML 的 `--detail` 或 export 参数：

| scope | 参数与取值 |
|---|---|
| `style_usage` | 必填 `--style-id`；`--include-descendants=true` 包含 based_on 后代，默认 false；`--cursor`、`--limit`，limit 默认 200、最大 1000；不接受 `--style-detail` |

```bash
lark-cli docs +local-fetch --doc "<token>" \
  --scope style_usage --style-id "<style_id>" --include-descendants=true
```
