# 本地 Word XML：普通块级内容控件

普通块级内容控件使用现有 `block_replace` 更新 children，不增加专用命令：

```xml
<content-control id="existing-record-id">
  <p>替换后的正文</p>
  <table>...</table>
</content-control>
```

- `id` 必填，必须来自最新 Fetch；仅允许更新已存在控件，不支持创建。
- 协议只拥有 children。alias、tag、lock、placeholder、data binding、control type 及未知未来元数据由宿主保留，不能写入或修改。
- children 复用现有 paragraph、list、table 等块级语法，不接受直接文本 child。
- `gallery=Table of Contents`、`gallery=Page Numbers*` 的控件及其后代仍由目录/页码领域能力管理，禁止通用 block mutation。
- inline/range content control、属性编辑及控件类型转换不在当前能力内。

写前读取完整控件和 children；写后核对控件 identity、非开放元数据及全部非目标 children 保持。

===== 全文完 =====
