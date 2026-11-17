# 修改本人签名、头像与名片背景图

`contact +update-self` 仅修改当前身份的个性签名、头像或名片背景图。UAT 用户和使用 AAT 的 Agent Employee 均走 `--as user`，AAT 修改的是智能伙伴自己的资料。不接受他人的 ID 或管理员模式。完整参数见 `lark-cli contact +update-self --help`。

## 只修改用户指定的字段

未传的字段保持原样；可以单独修改签名，不需要附带头像。显式传空签名表示清空；背景图传空 key 表示恢复默认背景。

```bash
lark-cli contact +update-self --description 'Working remotely' --as user
lark-cli contact +update-self --description '' --as user
```

- 本流程调用 `PATCH /open-apis/directory/v1/employees/{当前用户 open_id}`，固定 `user_auth_type=user`。旧 `/contact/v3/users` 的自助更新字段限制不适用于这个流程。
- 企业后台禁止员工编辑的字段会被服务端拒绝。保留原生错误，不切换管理员身份或改用其他接口绕过限制。

## 头像与背景图

```bash
lark-cli contact +update-self --avatar-file ./avatar.png --background-image-file ./background.png
lark-cli contact +update-self --avatar-key img_xxx --dry-run
lark-cli contact +update-self --background-image-key '' --as user
```

- 每种图片的本地文件与已有 image_key 二选一。头像和背景图 key 均来自 `image_type=avatar` 上传，本命令上传文件时自动使用该类型，以获得可在个人名片中显示的图片资源。
- `--background-image-key ''` 恢复默认名片背景，不读取或上传图片；未传该参数则保留当前背景。
- 单个文件必须为非空普通文件，最多 10 MiB；不能把图片 URL 当成本地路径。图片格式与像素限制由服务端校验。`--dry-run` 只预览计划，不读取图片或上传。
- 所有指定文件读取和关闭完成后才开始上传；以最终资料更新结果为准。更新失败后不要自动重试或报告已完成。
