# 前端开发指南

本文档介绍 AI 表格数据源连接器插件前端的开发规范与实现要点。

## 简介

数据源连接器插件需要提供一个**前端单页面**，在用户配置数据源同步时会唤起该页面，用于展示自定义的数据源配置 UI。

通过官方 npm 包 `dingtalk-docs-cool-app` 提供的方法，前端页面可以与 AI 表格宿主环境通信，完成插件初始化和配置参数的保存。

## 快速开始

### 安装依赖

要求 `dingtalk-docs-cool-app` 版本 **>= 0.3.16**。

```bash
pnpm add dingtalk-docs-cool-app@latest
```

### 使用官方模板

推荐直接 fork 官方示例项目快速启动：

[dingdocs-notable/datasource-plugin-demo](https://github.com/dingdocs-notable/datasource-plugin-demo)

---

## 核心 API

### `initView` — 初始化插件环境（必须调用）

在前端页面**首次渲染时**必须调用此方法，完成插件环境初始化。若未调用，AI 表格将无法识别该页面为数据源连接器插件。

```typescript
import { initView } from 'dingtalk-docs-cool-app';

initView({
  onReady: () => {
    console.log('插件环境初始化完成');
  },
  onError: (e) => {
    console.error('初始化失败', e);
  },
});
```

---

### `dataSource.saveConfigAndGoNext` — 保存配置并进入下一步（必须调用）

用户完成配置后，调用此方法将配置持久化保存，调用后会关闭配置页面并自动跳转到字段映射步骤。每次触发数据同步时，后端接口将接收到此配置（作为 `params`）。

```typescript
await Dingdocs.base.host.dataSource.saveConfigAndGoNext(config, options?);
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `config` | `unknown` | ✅ | 数据同步配置参数，格式由开发者自定义，平台不解析 |
| `options.accountId` | `string` | 否 | 要绑定到本次数据源的账号 ID（使用三方账号代管时传入） |

---

### `dataSource.getSyncConfig` — 获取同步配置（按需调用）

获取当前数据源已保存的同步配置，用于在**用户编辑已有同步表时回显将当前配置**。

```typescript
const config = await Dingdocs.base.host.dataSource.getSyncConfig<T>();
```

#### 使用时机

应在 `initView` 的 `onReady` 回调中调用。首次创建时尚无已保存配置，属于正常情况，需用 `try/catch` 包裹。

#### 典型用法

```typescript
type SyncConfig = { tableName: string; /* ...other fields */ };

const [syncConfig, setSyncConfig] = useState<SyncConfig | null>(null);

initView({
  onReady: async () => {
    try {
      // 编辑已有同步表时，返回上次 saveConfigAndGoNext 保存的配置
      const config = await Dingdocs.base.host.dataSource.getSyncConfig<SyncConfig>();
      if (config) setSyncConfig(config); // 用于表单回显
    } catch {
      // 首次创建时尚无已保存配置，属于正常情况
    }
  }
});

// 保存配置（创建 / 更新同一方式）
const newConfig: SyncConfig = { tableName: 'users' };
await Dingdocs.base.host.dataSource.saveConfigAndGoNext(newConfig);
```

> **返回内容**：返回的配置与上次调用 `saveConfigAndGoNext` 时传入的 `config` 完全一致，类型由开发者自定义。

---

### `$CORPID$` — 获取当前企业 ID（按需使用）

在插件 URL 中嵌入 `$CORPID$` 占位符，AI 表格加载前端页面时会自动替换为当前组织的 `corpId`。

```
# 配置的 URL
https://xxx.com?corpId=$CORPID$

# 实际加载时
https://xxx.com?corpId=dingxxxx
```

---

### `getAuthCode` — 获取用户免登码（按需调用）

在企业内插件或三方企业插件场景下，可调用此方法获取当前用户的免登码，基于免登码实现免密登录。

```typescript
const authCode = await Dingdocs.base.host.getAuthCode(corpId);
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `corpId` | `string` | 当前企业 ID，可通过 `$CORPID$` 占位符获取 |

详见钉钉开放平台文档：[SSO 单点登录概述](http://open.dingtalk.com/document/development/sso-overview)

遇到 `getAuthCode` 无法获取免登码的情况，请参考 [`docs/faq.md` — 前端常见问题](../docs/faq.md)。

---

## 三方账号代管（可选能力）

当数据源需要依赖**外部三方平台的账号、令牌、AK/SK 等身份凭证**进行数据拉取时，可选择使用此能力，将凭证托管给钉钉一方加密存储。

**核心优势**：
- 凭证不在前端明文展示，由钉钉一方负责加密存储
- 账号绑定到数据源后，每次同步时后端 `context.credentials` 自动注入凭证明文
- 支持账号复用（一个账号可绑定多个数据源）

> 此功能为**可选能力**，若数据源无需第三方账号凭证，可完全忽略本章节。

所有账号管理方法挂载在 `Dingdocs.base.host.dataSource.account` 上。

---

### `account.list` — 获取账号列表

```typescript
const accounts = await Dingdocs.base.host.dataSource.account.list();
// 返回：{ accountId: string; name: string; avatar?: string }[]
```

---

### `account.create` — 创建账号

```typescript
const { accountId } = await Dingdocs.base.host.dataSource.account.create({
  name: '我的账号',
  credentials: {
    apiKey: 'sk-xxx',       // 凭证结构由插件自行定义
  },
});
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | `string` | ✅ | 账号显示名称 |
| `credentials` | `Record<string, string>` | ✅ | 身份凭证键值对，格式由插件自行定义，钉钉一方原样加密保存。后端 `context.credentials` 内容与此一致 |

> ⚠️ **安全约束**：账号创建后凭证不再明文展示，只支持**重命名**和**删除**。如需更新凭证，请删除后重新创建。

---

### `account.rename` — 重命名账号

```typescript
await Dingdocs.base.host.dataSource.account.rename(accountId, '新名称');
```

---

### `account.remove` — 删除账号

```typescript
await Dingdocs.base.host.dataSource.account.remove(accountId);
```

> ⚠️ 删除账号前请确认该账号未被任何数据源绑定，否则下次同步时将无法获取凭证。

---

### `account.getCredentialToken` — 获取动态凭证 Token（按需调用）

**使用场景**：配置面板需要根据已选账号动态拉取数据（如展示可同步的表列表），但前端不能持有明文凭证。此方法向钉钉一方换取一个**短时效加密 token**，传给插件服务端由其解密后调用三方 API。

```typescript
const { credentialToken } = await Dingdocs.base.host.dataSource.account.getCredentialToken(accountId);
```

| 字段 | 说明 |
|------|------|
| `credentialToken` | 有效期 **5 分钟**的凭证 token。若在开放平台配置了 `encryptionKey`，则为加密密文；否则为明文凭证 JSON 的 Base64url 编码 |

**使用流程：**

```
① account.getCredentialToken(accountId)  →  AI 表格服务端返回短时效 token
② 将 token 传给插件服务端（如 POST /api/tables）
③ 插件服务端解密 token → 明文凭证 → 调用三方 API → 返回数据
```

**开放平台配置（启用加密）：**

要使用加密版 token，需在开放平台的酷应用配置页中填写 `encryptionKey`。配置方式详见插件发布指南。

> 未配置 `encryptionKey` 时，token 为明文 Base64url 编码，仅建议用于开发测试。

**示例：**

```typescript
const handleAccountSelect = async (accountId: string) => {
  const { credentialToken } = await Dingdocs.base.host.dataSource.account.getCredentialToken(accountId);

  const { tables } = await fetch('/api/tables', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credentialToken }),
  }).then(res => res.json());

  setAvailableTables(tables);
};
```

插件服务端解密 `credentialToken` 的方法，见后端开发指南「[动态查询凭证 Token 解密](backend-developer-guide.md)」章节。

---

### 账号绑定到数据源

账号创建后，通过 `saveConfigAndGoNext` 的 `options.accountId` 将账号与当前数据源绑定。绑定后后端 `context.credentials` 将在每次同步时自动注入。

```typescript
const { accountId } = await Dingdocs.base.host.dataSource.account.create({
  name: '生产账号',
  credentials: { accessKey: 'AKxxx', secretKey: 'SKyyy' },
});

await Dingdocs.base.host.dataSource.saveConfigAndGoNext(
  { tableName: 'orders' },  // 自定义配置
  { accountId },             // 绑定账号
);
```

---

### 典型 UI 交互流程

```
用户打开配置页
  ├── account.list() 展示已有账号
  │     ├── 有账号 → 用户选择 accountId
  │     └── 无账号 → 用户填写凭证 → account.create() → 得到 accountId
  ├── （可选）account.getCredentialToken(accountId)
  │     → 传给插件服务端 → 动态拉取表列表等数据
  ├── 用户填写其他配置
  └── 点击「下一步」→ dataSource.saveConfigAndGoNext(config, { accountId })
```

---

## 完整示例

以下示例实现了一个最简配置页面，涵盖插件初始化、数据表选择和配置保存。

```typescript
import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { initView } from 'dingtalk-docs-cool-app';

const tableNames = ['user', 'order', 'product'];

function App() {
  const [tableName, setTableName] = useState<string>(tableNames[0]);

  useEffect(() => {
    initView({
      onReady: () => console.log('插件环境初始化完成'),
      onError: (e) => console.error('初始化失败', e),
    });
  }, []);

  const handleNext = async () => {
    await Dingdocs.base.host.dataSource.saveConfigAndGoNext({ tableName });
  };

  return (
    <div>
      <h1>数据源连接器配置</h1>
      <label>请选择需要同步的数据表</label>
      <select value={tableName} onChange={(e) => setTableName(e.target.value)}>
        {tableNames.map((name) => (
          <option key={name} value={name}>{name}</option>
        ))}
      </select>
      <button onClick={handleNext}>下一步</button>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```
