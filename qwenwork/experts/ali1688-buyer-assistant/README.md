# 1688 买家助手（UTP 整合版）

为 1688 买家提供一站式采购能力，在 1688 官方套件基础上整合 UTP 交易闭环。

## 前置条件

套件已内置 macOS 与 Windows 两个平台的 UTP 连接器二进制（`bin/utp` + `bin/utp.exe`），无需额外安装 Node.js 或 npm。请在套件详情页按当前操作系统启用对应的连接器：
- **macOS** → 启用「UTP Connector (macOS)」
- **Windows** → 启用「UTP Connector (Windows)」

ali1688-buyer 连接器为远程 HTTP，无需安装。

## 能力概览

| Skill | 能力 | 连接器 |
|---|---|---|
| 智能选品 (1688-product-find) | 文本搜索 / 图搜 / 链接找同款 / 比价 | 文本搜→UTP；图搜/链接/比价→1688 |
| 找供应商 (1688-source-suppliers) | 查询供应商及工厂信息 | 1688 |
| 采购寻源 (1688-sourcing-inquiry) | 采购询盘寻源 | 1688 |
| 分销经营 (1688-distribution) | 选品铺货 / 订单 / 旺旺 / 知识库 | 1688 |
| 88生意通 (1688-syt) | 线下采购单全生命周期 | 1688 |
| 智能采购专家 (utp-shopping) | 加购→下单→支付端内交易闭环 | UTP |

## 连接器

- **ali1688-buyer** (streamable-http + OAuth)：1688 官方 22 工具
- **utp-shopping-connector** (stdio, macOS)：UTP 交易闭环，使用套件内置 `./bin/utp`
- **utp-shopping-connector-win** (stdio, Windows)：UTP 交易闭环，使用套件内置 `.\bin\utp.exe`

详见 [CONNECTORS.md](CONNECTORS.md)。

## 技术基座

本套件以 UTP 为交易闭环技术基座：能用 UTP 的能力优先走 UTP（文本搜索、加购、下单、支付），UTP 暂不具备的能力（图搜、找供应商、询盘、分销、88生意通）保留 1688 官方网关兜底，后续 UTP 补齐后逐个替换。
