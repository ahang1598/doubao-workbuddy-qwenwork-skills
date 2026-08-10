# +get-user

按 ID 取用户基本信息(姓名等)。

```bash
# 取自己
lark-cli contact +get-user --as user
```

## 注意事项

- **按 ID 取他人请用 `+search-user --user-ids <id>`**,字段比本命令多(部门 / 邮箱 / 是否激活等)。本命令只回很少字段。
