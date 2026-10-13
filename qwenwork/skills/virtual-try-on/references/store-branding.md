# 装扮店铺（设置品牌信息）

## 品牌信息字段

| 字段 | 说明 | 展示位置 | 必填 |
|------|------|----------|------|
| 店铺名称 | 品牌名 | 首页顶部品牌区 | ✅ |
| 店主说（slogan） | 一句话品牌宣言 | Hero 区域文案 | ❌（默认：穿得好看，是对自己最好的投资） |
| 店铺 logo | 方形小图标，建议 1:1 | 首页顶部品牌区 + Hero 区 | ❌（默认渐变占位图） |
| 店铺照片 | 门头/店内实景 | Hero 大图区 | ❌（建议提供，大幅提升品牌质感） |
| 店铺视频 | 店铺宣传视频 | Hero 区域 | ❌ |
| 微信号 | 联系方式 | 顾客联系页 | ❌ |
| 店铺地址 | 实体店地址 | 顾客联系页 | ❌ |

## 首次设置引导

检查记忆中是否已有店铺信息：
- ✅ 已有 → 直接使用已有信息调用 API 更新
- ❌ 没有 → 使用 `ask_human` 询问用户

```
ask_human: 🏪 接下来请提供店铺品牌信息，设置后会显示在试衣间首页，提升店铺品牌形象：

【品牌门面】（建议都填，让顾客一眼记住你的店）
1. 店铺名称（必填）：例如「沁心女装」
2. 店主说（slogan）：例如「穿得好看，是对自己最好的投资」（不填将使用此默认值）
3. 店铺 logo / 头像：方形小图标，建议 1:1 正方形图片（图片URL或本地路径，不填则使用默认渐变占位图）
4. 店铺照片：店铺门头/店内实景照片（图片URL或本地路径，不填则不展示，但建议提供，会大幅提升品牌质感）

【联系信息】（顾客试穿后联系你的方式）
5. 微信号
6. 店铺地址

（除店铺名称外都是可选项，不需要的直接回复"跳过"即可）
```

## 图片上传前置处理

如果用户提供了店铺 logo 或店铺照片（本地文件路径或图片 URL）：
1. **图片审核**：
   - 不能包含色情、暴力、政治敏感等违规内容
   - 店铺照片必须是真实店铺/门头/店内实景
   - 店铺 logo 必须是品牌图标/头像类图片，不能是无关图片
2. **上传钉钉**：使用 `dt_media_upload` 上传得到公网 URL（格式 `https://down.dingtalk.com/media/xxx.png`）

## 命令

```bash
# 全量更新
python scripts/cli.py try-on store-update \
  --shop-name "店铺名称" \
  --slogan "店主说内容" \
  --shop-logo-url "https://down.dingtalk.com/media/logo.png" \
  --shop-image-url "https://down.dingtalk.com/media/xxx.png" \
  --shop-video-url "https://down.dingtalk.com/media/video.mp4" \
  --wechat "微信号" \
  --shop-address "店铺地址"

# 单字段更新（不传的字段保留原值）
python scripts/cli.py try-on store-update --slogan "用心搭配，遇见更美的自己"
python scripts/cli.py try-on store-update --shop-logo-url "https://down.dingtalk.com/media/logo.png"
python scripts/cli.py try-on store-update --shop-image-url "https://down.dingtalk.com/media/xxx.png"
python scripts/cli.py try-on store-update --shop-name "沁心女装" --slogan "穿得好看，是对自己最好的投资"
python scripts/cli.py try-on store-update --shop-video-url "https://down.dingtalk.com/media/video.mp4"
```

## 记忆管理

更新成功后，将店铺信息存入记忆，后续不再重复询问：
```
店铺信息：店铺名称=xxx，店主说=xxx，店铺logoURL=xxx，店铺照片URL=xxx，店铺视频URL=xxx，微信号=xxx，店铺地址=xxx
```

如果用户明确表示跳过，也记录到记忆中（标记为"用户选择不设置店铺信息"）。
