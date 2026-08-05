# Skill 埋点说明

本文描述 **1688-open-skill-template** 中 Skill 调用埋点的上报时机、请求内容与失败策略，便于对接网关统计与二次开发对齐行为。

## 1. 作用概述

埋点用于在 **Skill 网关**侧统计 Skill 被调用的次数与基础元信息（名称、版本、渠道、场景）。实现集中在 `scripts/_tracker.py` 的 `report_skill_usage()`，由统一 CLI 入口 `cli.py` 在命令生命周期末尾触发。

## 2. 上报时机

| 场景 | 是否上报 | 说明 |
|------|----------|------|
| 已识别子命令（如 `configure`、`get_core_metrics`），且子命令 `main()` **正常执行完毕**（无未捕获异常、未中途 `sys.exit`） | **是** | 无论业务 JSON 中 `success` 为 `true` 或 `false`（例如 AK 未配置、参数校验失败等只要进程未崩），均在子命令返回后上报一次。 |
| 未传入子命令、子命令名不在注册表、或展示用法后 `sys.exit(1)` | **否** | `cli.py` 在调用子模块前即退出，不会执行埋点逻辑。 |
| 子命令内 `argparse` 报错并 `sys.exit`（如必填参数缺失） | **否** | 进程在 `module.main()` 内退出，**不会**回到 `cli.py` 的埋点代码。 |
| 子命令 `main()` 抛出**未捕获**异常 | **否** | 异常向上传播，埋点代码未执行。 |

**小结**：埋点表示「一次 CLI 子命令入口已跑完主流程」，偏 **会话级 / 调用次数** 统计，**不**区分具体子命令名（请求体中无命令字段），也**不**保证业务一定成功。

## 3. 上报接口与传输

| 项 | 值 |
|----|-----|
| 方法 | `POST` |
| 路径 | `/api/reportSkillsUsage/1.0.0` |
| 完整 URL | 与业务 API 相同网关：`https://pre-skills-gateway.alibaba-inc.com` + 路径（见 `scripts/_http.py` 中 `BASE_URL`） |
| 请求体 | JSON，`Content-Type: application/json; charset=utf-8` |
| 鉴权 | 与能力调用一致：通过 `get_auth_headers()` 注入签名；**未配置 AK 时** `api_post` 会抛鉴权类异常，由埋点模块捕获（见下文），**不会**向网关发出 HTTP 请求。 |

网络层对 **连接错误 / 超时** 有有限次重试（与 `_http.api_post` 一致）；HTTP 4xx/5xx 或业务 `success: false` 会转为异常并由埋点侧吞掉。

## 4. 请求体字段

上报 JSON 字段与含义如下（与代码一一对应）。

| 字段 | 类型 | 取值说明 |
|------|------|----------|
| `apiName` | `null` | 固定为 JSON `null`，占位或网关约定字段。 |
| `skillsName` | string | Skill 名称，来自环境变量 `SKILL_NAME`，缺省为 `1688-open-skill-template`。 |
| `version` | string | Skill 版本，来自 `SKILL_VERSION`，缺省为 `1.0.0`。 |
| `scene` | string | 固定为 `"CLI"`，表示当前模板通过命令行入口触发。 |
| `channel` | string | 发布渠道，来自 `SKILL_CHANNEL`，缺省为 `clawhub`。 |

**环境变量来源**：模块加载时会读取项目根目录 `.env` 并写入 `os.environ`（**不覆盖**已存在的环境变量，便于 CI/CD 注入覆盖本地文件）。

## 5. 失败与日志策略

- `report_skill_usage()` 整体包裹在 `try/except` 中：**任意异常均不向外抛出**，主命令的退出码与输出不受影响。
- 失败时通过 logger `1688_tracker` 输出 **DEBUG** 级别日志：`埋点上报失败（已忽略）: ...`。
- `cli.py` 在调用 `report_skill_usage()` 外层还有一次 `try/except`，避免导入埋点模块等极端情况影响进程。

若需在本地排查埋点，可将日志级别调到 DEBUG 并关注 `1688_tracker` / `1688_http`。

## 6. 与模板扩展的关系

新增 `capabilities/<name>/cmd.py` 并注册命令后，只要仍由根目录 `cli.py` 统一调度且在子命令 `main()` 正常返回后回到 `cli.py`，**会自动沿用同一套埋点**，无需在子命令内重复调用。

若希望按子命令或按业务结果细分统计，需要在网关契约允许的前提下扩展请求体或增加独立埋点逻辑（当前模板未实现）。

## 7. 相关文件索引

| 文件 | 职责 |
|------|------|
| `scripts/_tracker.py` | 读取 `.env`、组装请求体、调用 `api_post` 上报。 |
| `cli.py` | 命令分发结束后调用 `report_skill_usage()`。 |
| `scripts/_http.py` | `api_post`：网关地址、签名、重试与错误映射。 |
| `SKILL.md` | 面向使用方的环境变量与埋点摘要。 |
