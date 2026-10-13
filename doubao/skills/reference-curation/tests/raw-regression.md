# 离线回归原始证据

## Command

```text
python3 tests/run_regression.py
```

## Result

- stdout: `{"ok": true, "should_trigger": 20, "should_not_trigger": 20, "boundary": 8, "regression": 4, "blocking_errors": 0}`
- return code: `0`
- stderr: 空
- assertion: `--qinyan-api-key` 不再出现在 CLI；中文 provider 缺失且强制门开启时返回 `2`；非法 ID/type/language/verification 返回 schema FAIL；中文姓名、学号、邮箱、手机号、Token、Home path、私网 IPv4、内网域名和私有绝对路径未出现在 stdout、stderr、JSON、Markdown/log 渲染中。
