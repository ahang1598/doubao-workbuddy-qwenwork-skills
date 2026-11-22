# 页面单条新增与附件上传

仅在用户明确要求把页面填写内容作为新记录写入 Base 时加载本文件；包含 `useSubmitBaseRecord`、录入字段与值编码、提交前校验及附件上传。编码前读取工程内的 `common/hooks/use-submit-base-record.ts`；需要附件上传时再读 `common/api`。通用开发流程见 [页面开发入口](../scenes/webpage.md)。

只支持新增单条记录，不支持更新已有记录、删除记录或批量写入。表、字段及选项使用已核实的元数据；资料不足时用 `+table-get` / `+field-list` / `+field-get` 补齐，选项可用 `+field-search-options` 查询。

## useSubmitBaseRecord：单条新增记录

```tsx
import { useSubmitBaseRecord } from "../common/hooks/use-submit-base-record";

const { submit, loading } = useSubmitBaseRecord({
  onSuccess: () => {
    // 仅成功时的 UI 更新放这里
  },
});

const onSubmit = async () => {
  await submit({
    tableId: "tblXXXX",
    fields: {
      fldTitle: title,
      fldAmount: amount,
      fldStatus: "已确认",
      fldTags: ["户外", "聚餐"],
      fldChecked: true,
      fldDate: new Date(),
      fldAttachments: [{ file_token: attachmentFileToken }],
      fldUsers: [{ id: selectedUserId }],
      fldRating: rating,
      fldPhone: phone,
      fldUrl: url,
      fldCurrency: currency,
      fldEmail: email,
      fldProgress: progress,
    },
  });
};
```

### 写入契约

- **可录入字段类型（完整）**：根据真实字段元数据确认类型，支持 Text / Number / SingleSelect / MultiSelect / Checkbox / DateTime / Attachment / User / Rating / Phone / Url / Currency / Email / Progress。这些是本文的字段分类名称，不要求 CLI 回包的 `type` 与其同名；缺元数据时先查询补齐。
- 不支持录入的字段省略对应控件、state、handler 与 payload 项；此范围不限制只读展示或查询交互。
- **静态可追溯 payload**：`submit({ tableId, fields })` 用字面 `tableId` 和静态真实字段 key（优先 `fieldId`，精确字段名也可），便于复制页面重映射，不使用计算键。
- **值编码**：Text → string；Number → 有限原始数字；Checkbox → boolean；DateTime → `Date` 或毫秒时间戳；SingleSelect → 已核实的选项显示名；MultiSelect → 已核实显示名数组；Attachment → `{ file_token: string }[]`；User → `{ id: string }[]`；Rating → 有限原始数字；Phone → string；Url → 链接串或 Markdown 链接串；Currency → 有限原始数字；Email → string；Progress → 有限原始数字。使用表单输入按类型编码，不提交格式化数字或直接复用某行单元格的 `originValue`。
- **SingleSelect / MultiSelect 编码**：单选提交一个已核实的选项显示名，多选提交已核实显示名数组；提交前将 UI token 映射为显示名。写入表示不接受 option ID / `optId`。
- **Attachment 来源**：附件先用下文的 `uploadAttachment` 拿到 `attachmentToken` 作为 `file_token`；**单个 Attachment 字段最多 100 个附件**。
- **User 来源**：人员先用 `searchUsers` 拿到 `userId` 作为 `id`，需要人员选择时读取 [数据规则](webpage-data.md) 的「人员搜索」。
- **调用时机**：Hook 在组件顶层声明，只在用户动作（如按钮 `onClick`）里调 `submit`；一个 hook 实例拒绝并发提交。
- **宿主行为**：新增成功后，同表 `useBaseData()` 自动刷新，`onSuccess` 里不要 `refetch()`。`submit()` 无返回值——仅成功的 UI 更新放 `onSuccess`，`onError` 只做额外失败副作用。失败已全局 toast 并 resolve（不抛错），所以不要另挂 `<Toaster />`、不要分支判断 `await submit()`、不要读返回的 `error`。

### 提交前校验

调用 `submit()` 前实现指令中的校验意图（必填、格式 / 范围、重复 / 唯一性、配额、可用性、资格、时间窗口等）。校验失败则反馈并不调用 `submit()`。依赖已有 Base 记录的校验，按 [数据规则](webpage-data.md) 用顶层 `useBaseData()` / 支持的 DSL 查询真实数据，不在提交 handler 或辅助函数内调用 Hook；不依赖 mock 数据、静态计数或 `submit()` 返回值。

## 附件上传 `uploadAttachment`

新增表单包含 Attachment 字段时，通过 `common/api` 导出的 API 上传附件，不直接 import 或调用底层 channel client。

```tsx
import {
  uploadAttachment,
  type UploadAttachmentResult,
} from "../common/api";
```

用 `File[]` 调用 `uploadAttachment(files)`，返回 `Promise<UploadAttachmentResult[]>`，与输入文件一一对应、顺序一致。

```tsx
const results = await uploadAttachment(Array.from(fileList));

results.forEach((result) => {
  if (result.status === "success") {
    // 上传成功：result.attachment.attachmentToken 作为 Attachment 字段写入的 file_token
    return;
  }
  // 上传失败：按 result.index 定位原文件并展示错误
  console.error(result.error.message);
});
```

成功结果含 `index` 与 `attachment`：

```tsx
interface UploadedAttachment {
  id: string;
  attachmentToken: string;
  name: string;
  mimeType: string;
  size: number;
  timeStamp: number;
  width?: number;
  height?: number;
  signatureExtra?: Record<string, unknown>;
}
```

失败结果含 `index` 与 `error: { code: "UPLOAD_FAILED"; message: string }`。

- 每个附件文件不超过 2 GB，调用前先校验文件大小、拒绝超限文件。
- 调用前把 `FileList` 转成 `File[]`。
- 选择或拖拽文件后自动开始上传。
- 一批可能同时有成功与失败，逐个结果独立处理，用 `index` 关联原文件。
- 上传中禁止重复提交，并暴露每个文件的 pending / uploading / success / failed 进度态。
- 附件上传依赖宿主 sandbox/iframe 通道，必须在该环境验证；本地浏览器直连可能没有宿主桥接。

## 构建前核对

- 单条新增只用支持录入的字段，值编码正确（Attachment 用 `file_token`、User 用 `{ id }`）。
- 校验在 `submit()` 前完成，成功 UI 更新放 `onSuccess`，同表查询由宿主自动刷新。
- 用到人员选择或已有记录校验时，已按需读取数据与人员搜索规则。
- 附件上传正确处理大小 / 数量限制、逐文件结果与上传状态。
- 没有引入任何更新 / 删除 / 批量写的伪交互。
