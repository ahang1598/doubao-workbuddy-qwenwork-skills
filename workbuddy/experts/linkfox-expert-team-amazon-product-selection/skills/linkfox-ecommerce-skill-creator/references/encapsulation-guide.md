# 脚本封装规范

> 借鉴 `browser-act-skill-forge` Phase 3a。
> 适用于 Tier 2 / Tier 3 skill 的 `scripts/*.py` 文件——做跨步骤的数据处理、参数解析、Tier 1 调用编排。
> Tier 1（单源 wrapper）由各 vendor 自己维护，不在本规范范围。

---

## 命名规则

- kebab-case：`get-product-detail.py`、`fetch-bsr-list.py`、`upload-listing.py`。
- 一个 .py 文件 = 一个原子能力，文件名描述能力本身。
- 文件名出现在 SKILL.md 中作为调用入口（`python scripts/get-product-detail.py {asin}`），所以对人也得可读。

---

## 两种封装方式

### 方式一：Python 直接干活（最常见）

argparse 入参 → HTTP 调用 / 本地处理 → 输出 JSON 到 stdout：

```python
import argparse
import json
import sys
import urllib.request

def main():
    sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser()
    parser.add_argument('asin', help='Amazon Standard Identification Number')
    parser.add_argument('--marketplace', default='US', help='US, UK, DE, JP...')
    args = parser.parse_args()

    try:
        # 实际业务逻辑
        result = call_linkfox_api(args.asin, args.marketplace)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 方式二：Python emit JS 字符串供浏览器 eval（仅当本 skill 含浏览器抓取节点时）

来源 `browser-act-skill-forge`，本规范不重复——直接看 `browser-act-skill-forge/references/output_template.md` "Python Wrapper File Template"。

要点：
- Python 只做参数化拼接，不做网络调用、不操作文件系统。
- JS 字符串在 f-string 中用 `{{` `}}` 转义大括号。
- JS 内部 try/catch，错误返回 `{"error": true, "message": "..."}`。

> 一般情况下，浏览器抓取应优先走团队已有的 Tier 1 vendor skill；自建 emit-JS 脚本仅在没有现成 Tier 1 时使用。

---

## 强制约束

### 错误返回结构

所有脚本出错时**返回 JSON，不要崩溃**：

```python
print(json.dumps({"error": True, "message": "..."}, ensure_ascii=False))
sys.exit(1)
```

理由：上游 agent 会捕获 stdout 解析；崩溃会让 agent 看到 stderr 噪音和非零退出，难以分辨"业务错误"与"工具坏了"。

### 输入参数语义化

argparse 参数名用业务术语，不要用技术术语：

| 应该 | 不应该 |
|------|--------|
| `asin` | `id`、`pk` |
| `keyword` | `q`、`query` |
| `marketplace` | `region`、`code` |
| `page` | `offset`、`cursor`（除非真的是 cursor） |

理由：agent 在 SKILL.md 里读到 `--marketplace US` 比读到 `--region US` 更容易判断对不对。

### 单一职责

一个脚本干一件事。不要写"瑞士军刀"型脚本（一个脚本根据 `--mode` 切换 5 种行为）。如果两个能力差异大 → 拆成两个 .py 文件。

### 无网络副作用约束（emit-JS 方式强制）

emit-JS 方式的 Python wrapper **只输出 JS 字符串**，**不发 HTTP 请求**、**不操作文件系统**、**不调浏览器**。这是 `browser-act-skill-forge` 的硬约束，移植过来。

直连 HTTP 的脚本可以发请求，但禁止：
- 不能写用户 home 目录之外的文件（除非用户显式同意）。
- 不能调三方代理服务、爬取平台（违反"直接操作目标站点"原则）。
- 不能在脚本里硬编码 API key——key 从环境变量或 `~/.config/<name>/` 读取。

---

## 大响应处理

满足落盘特征任一条 → 不要把完整响应直接打印到 stdout，落盘后只打印摘要：

- 字段数 ≥ 10
- 含数组返回
- 含分页
- 含长文本（描述、评论、HTML）
- 输出会被下游步骤复用

落盘统一通过产物自带的 `scripts/response_io.py`。模板见 `large-response-snippet.md`。

调用样例：

```python
from response_io import save_and_summarize

result = call_api(...)
summary = save_and_summarize(
    result,
    save_path=f'tmp/product-{args.asin}.json',
    preview_fields=['title', 'price', 'rating', 'review_count'],
)
print(json.dumps(summary, ensure_ascii=False))
```

---

## 反模式

- 一个 .py 写 800 行业务逻辑 → 拆 helper 模块到 `scripts/_lib/`。
- argparse 用 `--debug`、`--verbose` 等开关 → skill 不需要 debug 模式，agent 不会用。
- print 中混 stderr 内容 → JSON 输出污染，agent 解析失败。
- API key 硬编码 → 永远不要。
- 同一份代码在 SKILL.md 和 scripts/ 各写一份 → SKILL.md 只写调用方式，代码只在 scripts/。
