# 插件能力升级指南（v1.0）

本文档帮助已完成首版开发的插件进行能力升级。每项升级相互独立，可按需选择。

---

## 升级一：context.fields 按需返回优化

### 价值

平台在调用 `/api/records` 时会在 `context.fields` 中传入用户实际选择的同步字段列表。适配后可以：
- **减少数据传输**：仅查询和返回平台需要的字段
- **直接获取字段类型**：无需额外调用 sheet_meta 或从数据推断类型

### 检测方法

检查后端 `RecordsRequest` 的 `Context` 类中是否包含 `fields` 字段。

### 适配步骤

1. **更新 Request Model**：在 records 接口的 Context 中新增以下字段：

```java
@Data
public static class RecordsContext {
    private String unionId;
    private String corpId;
    private Map<String, String> credentials;
    // --- 以下为新增字段 ---
    private String locale;
    private String docKey;
    private String sheetId;
    private String syncInstanceId;
    private String taskId;
    private List<SyncField> fields;
    private Integer maxImportRowCount;
}

@Data
public static class SyncField {
    private String id;
    private String type;
}
```

> `sheet_meta` 接口的 Context 只需 `unionId`、`corpId`、`credentials`、`locale`、`docKey`、`sheetId`。

2. **按需过滤返回字段**：

```java
List<SyncField> syncFields = request.getContext().getFields();
if (syncFields != null && !syncFields.isEmpty()) {
    Set<String> requiredIds = syncFields.stream()
        .map(SyncField::getId)
        .collect(Collectors.toSet());
    record.getFields().keySet().retainAll(requiredIds);
}
```

3. **利用字段类型信息**（可选）：

```java
// 无需再调 sheet_meta 获取类型，直接从 context.fields 中读取
Map<String, String> fieldTypeMap = syncFields.stream()
    .collect(Collectors.toMap(SyncField::getId, SyncField::getType));
```

> **兼容性**：`context.fields` 可能为 null（旧版平台不传），务必做空判断。

---

## 升级二：Manifest errorMessages 国际化

### 价值

在 manifest 中配置错误码对应的国际化文案后，用户看到的错误弹窗将展示**插件自定义的、当前语言的友好文案**，而非后端返回的原始 msg。

### 检测方法

检查 `manifest.json` 中是否有 `manifest.base.dataSource.errorMessages` 和 `i18nMap` 配置。

### 适配步骤

1. **在 manifest.json 中添加 errorMessages 和 i18nMap**：

```json
{
  "manifest": {
    "base": {
      "dataSource": {
        "errorMessages": {
          "10006": "${{errormsg_10006}}",
          "10007": "${{errormsg_10007}}",
          "10008": "${{errormsg_10008}}"
        }
      }
    }
  },
  "i18nMap": {
    "zh-CN": {
      "errormsg_10006": "认证失败，请检查用户名和密码",
      "errormsg_10007": "连接超时，请检查网络和IP白名单",
      "errormsg_10008": "服务繁忙，请稍后重试"
    },
    "en-US": {
      "errormsg_10006": "Auth failed. Check username and password.",
      "errormsg_10007": "Connection timed out. Check network.",
      "errormsg_10008": "Service busy. Try again later."
    },
    "ja-JP": {
      "errormsg_10006": "認証失敗。ユーザー名とパスワードを確認してください。",
      "errormsg_10007": "接続タイムアウト。ネットワークを確認してください。",
      "errormsg_10008": "サービスが混雑中。しばらく後に再試行してください。"
    }
  }
}
```

### ⚠️ 关键约束

| 约束 | 说明 |
|------|------|
| **key 必须用下划线 `_`** | 禁止使用连字符 `-`！平台用 nunjucks 渲染模板，`${{errormsg-10006}}` 会被解析为减法运算，输出 `NaN` |
| **文案尽量简短** | 建议 ≤ 30 字中文，弹窗空间有限 |
| **errorMessages key 为字符串** | 对应后端接口返回的 `code` 值，范围建议 10006~10099 |

### 文案解析优先级

平台按以下顺序确定用户看到的错误文案：

1. ✅ manifest `errorMessages[code]` 的国际化文案（推荐）
2. 插件接口返回的 `msg` 字段
3. 系统内置 code 的默认文案（仅 10001~10005）
4. 平台默认错误提示

---

## 升级三：已有 manifest 中 i18nMap key 格式修正

### 检测方法

检查 manifest.json 中 `i18nMap` 的 key 是否包含连字符 `-`。

### 修正方式

将所有 `errormsg-100xx` 格式改为 `errormsg_100xx`：

```diff
- "errormsg-10006": "认证失败"
+ "errormsg_10006": "认证失败"
```

同步修改 `errorMessages` 中的模板引用：

```diff
- "10006": "${{errormsg-10006}}"
+ "10006": "${{errormsg_10006}}"
```
