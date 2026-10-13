# 企查查 (QCC) 连接器启用指南（QoderWork 原生连接器）

在 QoderWork 中，企查查是**原生市场连接器**（显示名 **Qichacha**，server 名 `qcc-company`），**无需**手动粘贴 JSON 或申请 API Key，走**一键连接 + OAuth 授权**。当会话工具列表中**检测不到**企查查工具，或连接器状态为 `needs-auth` / 未启用时，按本文引导用户完成授权。

## 判断当前状态

用 `qw_query` 查询连接器状态：

```
qw_query({ key: "qoderwork.settings.connector.market.qcc-company" })
```

关注返回中的字段：

- `installed`：是否已安装（原生连接器通常已内置为 true）
- `enabled`：是否启用
- `status`：
  - `connected` → 已授权可用，直接进入查询
  - `needs-auth` → 已启用但**未授权**，需引导用户完成 OAuth 授权
  - `disabled` → 未启用，需先启用再授权
- `auth.authType`：`oauth`（企查查为 OAuth，不是 API Key）

## 引导用户启用与授权

1. **启用（若 `disabled`）**：

   ```
   qw_action({ key: "qoderwork.settings.connector.market.qcc-company", action: "enable" })
   ```

2. **打开连接器页面让用户授权**：

   ```
   qw_action({ key: "qoderwork.settings.connector.market.qcc-company", action: "open" })
   ```

   或直接引导用户：**QoderWork → 设置 → 连接器 → 行业数据 → Qichacha（企查查）→ 点击「连接 / 授权」**，在弹出的企查查 OAuth 页面登录并授权。

3. **等待授权完成**：OAuth 需要用户在浏览器中登录企查查账号并点击授权。完成后连接器 `status` 变为 `connected`，工具列表随即出现企查查工具，**无需重启 QoderWork**。

## 授权完成后的可用性自检

重新查询工具列表或连接器状态，`status = connected` 即视为可用。企查查连接器会暴露一批工具（企业搜索、工商登记、股权、人员、风险、经营、知识产权等），本技能按 [dimension-tool-map.md](dimension-tool-map.md) 的**描述关键词**匹配，不依赖固定工具名。标志性入口能力：

- 模糊搜索企业（描述含「搜索 / 企业查询 / by query」，通常返回 ≤5 条候选）
- 工商登记信息（描述含「工商 / registration / 企业基本信息」）

## 说明：与旧版（多 server）接入方式的差异

- 旧版通过「设置 → MCP 服务 → 添加 JSON + Bearer API Key」接入，并拆成 `qcc-company` / `qcc-risk` / `qcc-ipr` / `qcc-operation` / `qcc-executive` / `qcc-history` 六个 server。
- QoderWork 原生连接器是**单一** `qcc-company` 连接器（OAuth），相关能力聚合在同一连接器下，**不要假设**存在上述独立 server 名；一律在企查查连接器的工具列表内按描述关键词匹配。
- 历史/变更等维度是否可用，取决于用户企查查账号的开通范围；不可用时按主流程跳过并标注，不阻断其他维度。
