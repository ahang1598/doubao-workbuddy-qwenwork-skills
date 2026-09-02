# Selector Fallback 机制

`selector` 支持 `string` 或 `string[]`，数组从前到后依次 `querySelectorAll`，第一个命中的立即生效。

## 修复规则

🔴 **禁止删除旧选择器**。旧选择器可能在当前 ASIN 失效但其他 ASIN 仍有效。

| 操作 | 正确 |
|------|------|
| 单值失效，追加新值 | `"old"` → `["new", "old"]` |
| 数组内某项失效，追加头部 | `["a", "b"]` → `["new", "a", "b"]` |

## 与 FIND_SELECTOR 协同

FIND_SELECTOR 返回的 candidates 按 confidence 降序，直接作为 selector 数组：

```
FIND_SELECTOR(field="brand") → [".po-brand"(0.95), "a#bylineInfo"(0.72)]
→ selector: [".po-brand", "a#bylineInfo"]
```
