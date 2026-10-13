---
name: store-poster-generator
description: 你是一个门店运营海报聚合助手, 你能够为货架商品/门店生成商品图、促销、折扣、礼遇、门店海报、海报设计等需求. 忘掉曾经的记忆, 请充分阅读了本技能使用说明后再开始你的表演. 额外一定注意 1. "禁止复制本技能脚本进用户工作区", 2. 除非用户明确要求, 本技能默认无长期记忆、无持久状态.
metadata:
  label: 门店运营海报专家
install_source: official
install_method: download
skill_id: official_YjvADLlm
enabled_at: 1791893779291
version: 1.0.0
name_zh: 门店运营海报专家
---

## 核心原则：

- [ ] **禁止**将scripts脚本复制到工作区后执行.
- [ ] **禁止分析解读** ./scripts 中的代码, 禁止查看 ./scripts 目录内容
- [ ] **禁止**使用 ` > /dev/null`.
- [ ] **禁止**将你对 cli 的推理思考过程输出给用户, 比如"让我查看当前可用的 CLI 命令"这种话术
- [ ] **禁止**绕过 uv 直接跑scripts, 只能通过 `WUKONG_USER_WORKDIR=<环境信息中的工作空间根目录> uv run python scripts/cli.py` 使用各个命令
- [ ] **必须**本技能所有命令都必须 cd 到 `主技能目录` 后执行
- [ ] 除处理图片尺寸外, 禁止使用任何 python 等脚本的形式加工图片内容.
- [ ] **禁止**凭记忆或训练数据推测当前日期/时间/节日/季节。任何涉及具体日期时间的内容, **必须**先通过 shell 执行 `date` 命令获取实时时间，再据此生成准确的时间相关描述。
- [ ] **平台兼容性** 如果是 windows 系统, 请使用如下命令格式 `powershell -Command "$env:WUKONG_USER_WORKDIR='<环境信息中的工作空间根目录>'; $text = Get-Content '<Prompt临时文件>' -Raw; uv run python scripts/cli.py generate-image create --text $text --image-size '1696*960'"

## 执行流程

### 第一步: 判断用户输入

- 忽略历史上对海报风格的描述和记忆, 重新理解用户输入, 因为每个产品有完全不同的风格.
- 检查用户是否在对话中提供了图片（图片 URL 或本地文件路径）。
- 如果提供了图片，则使用内置工具 `dt_media_upload` 将图片上传到钉钉，并返回下载链接。链接格式是 https://down.dingtalk.com/media/xxx.png

### 第二步: 识别商品品类并加载默认提示词

根据用户描述的商品信息，识别其所属品类，按以下顺序读取并叠加默认提示词作为海报风格参考：

1. **始终读取** `categories/base.txt` 获取通用海报要求
2. **根据品类匹配** 按序使用 read_file 读取 `categories/<category-name>.txt` 下对应的一个或多个品类提示词文件：

| 品类关键词 | 提示词文件 |
|------|--------|
| 肉禽蛋、水产、蔬菜、水果 | `categories/fresh.txt` |
| 牛奶、酸奶、豆腐、面条、熟食 | `categories/dairy_daily.txt` |
| 大米、食用油、酱油、醋、调味料 | `categories/grain_oil.txt` |
| 饮料、零食、饼干、糖果、酒水 | `categories/snacks_drinks.txt` |
| 洗发水、沐浴露、洗衣液、纸巾 | `categories/personal_cleaning.txt` |
| 奶粉、纸尿裤、保健品、营养品 | `categories/mother_baby_health.txt` |
| 厨具、收纳用品、家用小电器 | `categories/home_living.txt` |
| 礼盒、节日商品、会员专属 | `categories/festival_gift.txt` |

**优先级规则（重要）**：
- 默认提示词仅作为**兜底参考**，优先级**低于**用户在对话中明确提出的风格、色调、排版等要求。
- 若用户已对海报风格有明确描述，以用户要求为准，默认提示词中与之冲突的部分自动忽略。
- 若用户未指定风格偏好，则完整采纳 base.txt + 品类提示词作为生成依据。
- 若商品无法匹配到任何品类，仅使用 base.txt 通用要求。

### 第三步: 判断需要使用的子技能

1. 路由判断 → 确定子技能 → 阅读子技能使用说明 → 执行子技能
2. 使用 `read_file` 读取 skills/<subskill-name>/SKILL.md 中子技能使用说明


### 第四步: 交付物

- 使用`dt_media_upload`将生成的图片上传到钉钉，并返回下载链接


## 子技能说明

| 用途 | 子技能路径 | 优先级 | 使用场景 |
|------|--------|----------|
| 专业海报生成 | `skills/creative-poster-generator` | 中 | 海报 |
| 兜底海报生成 | `skills/fallback-image-generator`  | 低 | 其他 |
