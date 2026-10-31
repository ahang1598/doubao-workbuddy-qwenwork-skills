# 记录附件管理命令

## 适用范围与原始文件要求

附件不作为普通 CellValue 写入；上传使用本地文件，下载／删除按 file token 或字段定位。

## 签字附件限制

写入或上传前用 `+field-get` 核对样式：`style.type=signature` 的签字附件单元格只读，不能上传或写入；限制见 [附件字段配置](field-config.md#attachment-字段)。

## 追加附件

命令片段：

`lark-cli base +record-upload-attachment --record-id <record_id> --field-id <field_id> --file <path>`

可重复 `--file` 一次追加多个附件，不能用普通记录操作接口写附件值。

## 下载附件

命令片段：

`lark-cli base +record-download-attachment --record-id <record_id> --file-token <file_token> --output <dir>`

不传 `--file-token` 时下载整行所有附件，也可重复 `--file-token` 只下载指定附件。Base 附件必须用这个命令下载，用其他下载入口可能失败。

## 删除附件

命令片段：

`lark-cli base +record-remove-attachment --record-id <record_id> --field-id <field_id> --file-token <file_token> --yes`

可重复 `--file-token` 一次删除同一单元格里的多个附件。
