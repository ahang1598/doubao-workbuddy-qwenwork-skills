# 离线验收契约

仅当需要校验一份候选输出，或新增、修改 fixture 时读取本文件。写作前不必加载。

## 目录

- [输入](#输入)
- [校验范围](#校验范围)
- [CLI 与退出码](#cli-与退出码)

## 输入

`scripts/validate_output.py` 接收一个 UTF-8 JSON fixture。fixture 顶层必须是对象，并包含：

- `id`：非空字符串且只能使用字母、数字、点、下划线和连字符；
- `category`：`positive`、`negative`、`boundary` 或 `regression`；
- `expected_route`：`trigger`、`not_trigger` 或 `boundary`；
- `candidate_output`：待校验文本；也可用 `--output` 指定 UTF-8 文本文件覆盖；
- `assertions`：对象，必须且只能包含 `required_substrings`、`forbidden_substrings`、`forbidden_regexes`、`max_output_chars` 和 `allow_empty_output`；
- `expected_valid`：布尔值，仅供 fixture 回归脚本断言退出码。

`assertions` 内三个列表的元素必须是非空字符串；`max_output_chars` 必须是正整数；`allow_empty_output` 必须是布尔值。未知顶层字段或 assertions 字段均判为无效，避免测试拼写错误被静默忽略。

可选字段：

- `description`：非空字符串，说明 fixture 用途；
- `privacy`：对象，含 `scan_standard_patterns` 布尔值与 `forbidden_literals` 字符串列表。未知字段禁止；
- `expected_issue_codes`：期望命中的问题代码列表；只要提供该字段（包括显式空列表），回归脚本就必须与实际问题代码精确匹配。

## 校验范围

校验器执行以下确定性检查：

1. fixture 结构、required、enum、ID、布尔值、nested field 与未知字段；
2. 必须出现和禁止出现的字符串；
3. fixture 给出的禁止正则表达式；非法正则直接判 fixture 无效；
4. 空输出和最大长度；
5. 明文敏感字面量；
6. 可选标准隐私模式：邮箱、中国大陆手机号、常见 Token、Home path、私网 IPv4、内网域名和私有绝对路径。

标准隐私模式不会推断某项个人信息是否业务必需，因此仅在 fixture 明确设置 `scan_standard_patterns=true` 时启用。用户确实要求在文书中保留联系方式等必要字段时，应关闭标准扫描，并把不应出现的具体明文放入 `forbidden_literals`。

校验器不判断模型是否真实调用 Skill，不替代豆包 Turbo 路由证据或 LLM judge，也不把 `exit code 0` 表述为模型质量已验证。它只证明候选输出通过当前 fixture 中可确定的断言。

本契约不是 JSON Schema，也不声称按 JSON Schema 校验。`load_fixture()` 以代码完整实现上列字段、类型、枚举、ID、嵌套字段和未知字段规则。fixture 不含 `final_ready`、`unresolved`、`conflict`、`claim_verified` 或证据新鲜度状态；这些状态既不在文书输出契约中，也不得由退出码推导。

## CLI 与退出码

调用：

```bash
python3 scripts/validate_output.py --fixture fixtures/positive/activity-summary.json
python3 scripts/validate_output.py --fixture fixtures/regression/privacy-redaction.json --output /path/to/candidate.txt
python3 scripts/run_fixtures.py
python3 scripts/contract_selftest.py
python3 scripts/privacy_selftest.py
```

- `validate_output.py --fixture`：必填；`--output` 可选，无默认值；未提供时读取 fixture 的 `candidate_output`。
- `run_fixtures.py --fixtures-dir`：可选，默认使用 Skill 根目录的 `fixtures`，递归发现其中的 `.json`；`--report` 可选，写入汇总 JSON。两个参数互不冲突。
- exit code `0`：候选输出没有命中问题；只代表当前断言通过。
- exit code `1`：候选输出命中一个或多个问题。
- exit code `2`：fixture、参数或输入文件无效，未完成候选输出验收。
- `run_fixtures.py` 只有在每个 fixture 的实际 VALID/INVALID 与 `expected_valid` 一致，且 `expected_issue_codes` 精确匹配时才返回 `0`。
- `contract_selftest.py` 无参数，覆盖 required、enum、ID、nested field、未知字段、非法正则、空输出与禁止文本；全部通过返回 `0`，任一失败返回 `1`。
- `privacy_selftest.py` 无参数，覆盖九类合成敏感模式；全部通过返回 `0`，任一失败返回 `1`。

脚本 stdout 和报告只写 fixture ID、VALID/INVALID、问题代码和计数；stderr 只写不含原输入的错误类型。禁止回显候选正文、路径值或敏感字面量。
