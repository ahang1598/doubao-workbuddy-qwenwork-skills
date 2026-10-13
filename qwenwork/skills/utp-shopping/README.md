# 智能采购专家 Skill

打通1688优质供给的 B2B 智能采购助手 Skill。源头好货、低价高性价比、供给有保障。用户通过自然语言与 Agent 对话，即可完成采购全流程——搜索商品、查看详情、加入购物车、下单结账，无需记忆任何命令。

本 Skill 与具体 Agent 应用解耦，可运行在任何支持 Skill 与 MCP 协议的 Agent 环境中（如 Claude Code、Cursor、Claude Desktop 等），不绑定单一厂商。

面向企业采购场景：用户的采购诉求往往是模糊的（"帮我买点办公用品"），Skill 会像懂行的导购一样先澄清关键约束（品类、预算、规格），再执行搜索与下单。

## 工作原理

用户用自然语言表达购物意图，Skill 将意图映射为底层购物工具调用并执行，再以结构化结果返回。工具细节对用户透明。

```
用户: "帮我搜一下螺丝"
  ↓ Skill 意图识别
调用商品搜索工具（keyword="螺丝"）
  ↓ 解析响应
展示搜索结果（表格 / 交互式卡片）
```

Skill 支持两种执行方式，按运行环境自动选择：

| 方式 | 适用场景 |
|------|----------|
| **MCP** | Agent 应用已连接 `utp` MCP Server，结果以交互式 UI 卡片呈现，用户可在卡片中直接操作 |
| **CLI** | 终端环境，通过 `utp` 命令行执行，结果以文本表格呈现 |

## 前置条件

本 Skill 自带跨平台一键安装脚本。`utp` CLI（MCP Server 也由该 CLI 启动）通过 npm 安装，安装脚本会在安装 CLI 后调用 `utp install` 完成 Skill 文件与 MCP Server 配置：

```bash
# macOS / Linux：指定目标 Host（推荐，多 Host 机器上必须指定）
bash <skill-dir>/scripts/install.sh --host qoderwork    # 或 qwenworkcn / claude-code / claude-desktop / cursor

# 不传 --host 时，按 Skill 所在路径识别当前 Host；识别不出才回退到按优先级探测
bash <skill-dir>/scripts/install.sh

# 所有探测到的 Host 都装
bash <skill-dir>/scripts/install.sh --all
```
```bash
# Windows（Git Bash）
bash <skill-dir>/scripts/install-win.sh
```

> 脚本会通过 npm 自动安装 CLI(`@ut-protocol/utp`) 并执行 `utp install`。加 `--reset` 可清除本地数据后全新安装。

MCP 方式的接入位置与格式因 Agent 应用而异（Claude Code、Cursor、Claude Desktop 等各不相同），由所在应用按其标准方式接入名为 `utp` 的 Server（启动命令 `utp mcp serve`，stdio 传输）。若应用不支持 MCP，自动回退到 CLI 方式。

## 支持的操作

| 操作 | 说话示例 |
|------|----------|
| 搜索商品 | "搜一下螺丝"、"有没有卖扳手的" |
| 查看详情 | "看看这个"、"这个有什么规格" |
| 加入购物车 | "来3个"、"买这个" |
| 直接购买 | "直接买下这个"、"下单买了" |
| 查看购物车 | "看看购物车" |
| 修改数量 | "改成5个" |
| 删除商品 | "把这个删掉" |
| 结账下单 | "结账"、"下单"、"就这些了" |
| 查询订单 | "订单怎么样了" |
| 取消订单 | "取消"、"不买了" |
| 批量查找 | "查一下这几个ID" |

## 购物流程

```
发现商业体 (discover)
    ↓
需求澄清（信息不足时）
    ↓
搜索商品 → 查看详情 → 选规格 → 加购物车
    ↓                              ↑
    ↓                          继续逛逛
    ↓
确认购物车 → 创建订单 → 绑定身份 (link) → 确认支付 → 完成
```

> 身份绑定（link）仅在真正下单（确认支付）时才需要；搜索、加购、创建结账全程无需买家身份。

## 数据流向

本 Skill 是用户本地 AI Agent 与商业体服务之间的**指令转换与展示层**，自身不采集、不上传、不留存用户数据到任何第三方。数据流向如下：

- **购物指令与商品数据**：用户的搜索词、加购/下单指令，经本地 `utp` CLI（或其启动的 MCP Server）发往用户所选择的**商业体服务 host**；商品、购物车、订单等数据由该 host 返回。host 由用户自行选择（见商业体注册表），Skill 不代替用户决定数据发往何处。
- **不经过额外中间方**：请求由本地 CLI 直连目标 host，Skill 层不引入任何自有服务器或数据中转。
- **AI 对话内容**：用户与 Agent 的自然语言对话，由所在 Agent 应用（如 Claude Code、Cursor 等）按其自身隐私政策处理，不在本 Skill 控制范围内。

## 本地存储与隐私

Skill 仅在用户本地 `~/.utp/` 目录下读写以下文件，**不上传、不同步到任何服务端**：

| 文件 | 内容 | 用途 |
|------|------|------|
| `~/.utp/config.json` | 会话配置、设备令牌缓存 | 供 CLI/MCP 发请求时读取注入 |
| `~/.utp/preferences.json` | 用户采购偏好的自然语言画像（品类倾向、预算区间、决策风格等） | 个性化推荐 |

- **偏好画像的产生**：Skill 在购物过程中观察用户表达，结账后会**先向用户提出猜测并请求确认**，用户同意后才写入 `preferences.json`；用户可随时要求修改或删除。
- **偏好画像的使用**：仅用于本地个性化推荐（标注常购品类、提示常选规格、预算偏离时提醒等），不参与鉴权，不外发。
- **删除**：删除 `~/.utp/preferences.json` 即清空全部偏好；删除 `~/.utp/config.json` 即清空鉴权配置。

## 安装 Skill

将本仓库放入所用 Agent 应用的 skills 目录。不同应用的目录位置不同（例如 Claude Code 为 `~/.claude/skills/`，其它应用请参考各自文档），以放入 Claude Code 为例：

```bash
git clone <repo-url> ~/.claude/skills/utp-shopping
```

安装后，在对话中直接表达购物意图（如"我要买东西"）即可触发；部分应用也支持以 `/utp-shopping` 斜杠命令唤起。

## 项目结构

```
.
├── SKILL.md                    # Skill 定义（MCP 工具用法、意图识别、流程规范）
├── references/
│   ├── registry.md             # 可用商业体注册表（host 列表）
│   ├── nomcp-model.md          # 无 MCP Apps 环境执行指南
│   ├── install-guide.md        # 安装与环境配置指导
│   └── error-guide.md          # 错误处理参考
├── scripts/
│   ├── install.sh              # macOS/Linux 一键安装（npm 安装 CLI + Skill + MCP，支持多 Host 自动探测和 --reset 重置）
│   └── install-win.sh          # Windows Git Bash 一键安装（含 Node.js LTS）
├── LICENSE
└── README.md
```

## 许可与免责

- 本项目基于 **Apache License 2.0** 开源，详见 [LICENSE](./LICENSE)。
- 本 Skill 仅提供购物指令的转换与展示，实际交易、支付、履约由用户选择的商业体服务提供，交易结果与商品质量由对应商业体负责。
- 使用者应自行确保对所连接商业体 host 的访问已获授权，并妥善保管本地鉴权配置。

## 参与贡献

欢迎提交 Issue 与 Pull Request，参与前请阅读 [贡献指南](./.github/CONTRIBUTING.md) 与 [行为准则](./.github/CODE_OF_CONDUCT.md)。安全问题请按 [安全政策](./.github/SECURITY.md) 私下报告。
