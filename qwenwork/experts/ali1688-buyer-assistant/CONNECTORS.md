# 连接器说明

本套件通过 `.mcp.json` 预配置了三个 MCP 连接器（macOS 两个 + Windows 两个），安装后自动注册到千问办公 / QoderWork。用户按当前操作系统启用对应的 UTP 连接器即可。

## 连接器一：ali1688-buyer（1688 官方）

- **协议**: MCP (Streamable HTTP)
- **端点**: `https://mcp.1688.com/mcp/qoderwork-buyer`
- **认证**: OAuth 2.1（安装后首次使用时触发授权流程，授权一次即可）
- **工具总数**: 22 个
- **承接能力**: 图搜 / 链接找同款 / 比价（智能选品）、找供应商、采购询盘、分销铺货、88生意通（线下采购单）

该 server 暴露 22 个独立工具，各 skill 在自己的 SKILL.md 中声明所需工具及调用规则，运行时 agent 直接按工具名调用。

## 连接器二：utp-shopping-connector（UTP 交易闭环 — macOS）

- **协议**: MCP (stdio，套件内置二进制)
- **命令**: `/bin/sh -c "chmod +x ./bin/utp; xattr -d com.apple.quarantine ./bin/utp; exec ./bin/utp mcp serve"`
- **二进制**: `bin/utp`（macOS arm64，已 ad-hoc 签名）
- **认证**: `utp_login` 扫码授权（下单支付时触发，搜索不需要）
- **承接能力**: 文本搜索（`utp_catalog_search` 语义搜索 + 交互卡片）、加购 / 下单 / 支付端内交易闭环

## 连接器三：utp-shopping-connector-win（UTP 交易闭环 — Windows）

- **协议**: MCP (stdio，套件内置二进制)
- **命令**: `.\bin\utp.exe mcp serve`
- **二进制**: `bin/utp.exe`（Windows x64）+ `bin/*.dll`（安全 SDK 依赖）
- **认证**: 同 macOS
- **承接能力**: 同 macOS

## 双连接器协作

- **文本搜索** → UTP `utp_catalog_search`（语义搜索 + 可点选加购的交互卡片）
- **图搜 / 链接找同款 / 比价** → 1688 `find_product`（UTP 暂不具备）
- **找供应商 / 采购询盘 / 分销铺货 / 88生意通** → 1688 网关（后续 UTP 补齐能力后逐个替换）
- **加购 / 下单 / 支付** → UTP `utp_cart_*` / `utp_checkout_*`（utp-shopping skill 承接）

> 套件内置双平台二进制，macOS 和 Windows 用户各启用对应连接器即可，无需安装 Node.js 或 npm。
