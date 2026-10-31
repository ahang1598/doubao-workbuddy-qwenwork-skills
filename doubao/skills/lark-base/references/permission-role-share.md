# 系统角色分享授权命令

## 作用与前置条件

本页维护系统角色分享授权的查询与修改。该设置控制分享能否授予高级权限系统角色，不会关闭高级权限，也不会替代自定义角色。调用者需要 Base 管理员权限，且 Base 已开启高级权限并具有系统角色。

## 查询与修改

以下示例展示读取、修改和回读的命令：

```bash
lark-cli base +advperm-share-get --base-token "<base_token>" --as user
lark-cli base +advperm-share-update --base-token "<base_token>" --enable-share=false --as user
lark-cli base +advperm-share-get --base-token "<base_token>" --as user
```

`--enable-share=true` 表示允许分享授权，`--enable-share=false` 表示禁止分享授权。
