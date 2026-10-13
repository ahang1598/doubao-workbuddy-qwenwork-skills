# 初始化店铺 & 获取二维码

## 初始化命令

```bash
python scripts/cli.py try-on init --output "store_qrcode.png" --mini-output "store_mini_qrcode.png"
```

## 返回字段

脚本返回 JSON：
- `qrcode_path`：H5 二维码 PNG 图片的绝对路径（顾客扫码在浏览器中打开店铺）
- `mini_qrcode_path`：小程序太阳码 PNG 图片的绝对路径（顾客扫码直接打开微信小程序店铺页面）

## 展示规则

1. 使用 `read_file` 读取 `qrcode_path` 渲染 H5 二维码图片展示给用户
2. 使用 `read_file` 读取 `mini_qrcode_path` 渲染小程序太阳码图片展示给用户

> ⚠️ 只展示二维码图片即可，禁止向用户输出店铺链接、storeId 等内部信息。

## 幂等说明

`init` 命令是幂等操作：
- 首次调用：创建店铺 + 生成二维码
- 再次调用：获取已有店铺的二维码（不会重复创建）

因此"获取二维码"和"初始化店铺"使用同一个命令。
