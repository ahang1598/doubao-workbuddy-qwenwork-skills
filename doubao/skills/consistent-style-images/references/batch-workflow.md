# 任务记录、提示词与批次（可选）

仅用于用户要求可追溯记录、结构化审核或大型批次恢复的任务。普通生图按 SKILL.md 直接执行，不需要 brief.json、batch.json、资料状态或文件指纹。下文是此高级模式的数据约定，不增加普通任务的确认步骤；方向明确时直接制作。

## brief.json：设计前任务单

每条影响结果的关键字段记录 `{value, state, source}`，state 为 confirmed/provided/proposed/pending。既有明确授权写入 source，不能让用户重答。

内容包括 brand、product、audience、objective、core_message、proof、tone、action（可 null）、channel、placement、deliverables、assets、copy_mode（verbatim/authorized_draft）、approval_mode（direct/sample_first）。允许未知信息，但涉及最终规格、事实或方向的关键未知应在交付前解决；无关字段不强迫填写。

首次品牌且方向不明确时交出具体文案和视觉方案再确认；样张优先模式等待样张确认；direct 模式自行检查后继续。流程阶段：brief → direction → copy → sample → batch → review。后续修改只返回受影响阶段；文案改动重排并重审，规格改变重做适配，品牌改变拆新批次。

## batch.json

```json
{
  "schema_version": 1,
  "brand_profile": "brand/profile.json",
  "brand_id": "example-brand",
  "profile_fingerprint": "",
  "rule_overrides": [],
  "stage": "concept",
  "brief": {"copy_status": "authorized_draft", "spec_status": "proposed", "source": "真实任务依据"},
  "expected_count": 1,
  "style_lock": {"direction": "本次具体方向", "fixed": ["字体层级", "按钮样式"], "variable": ["主题对应视觉"]},
  "jobs": [{
    "id": "01", "theme": "本次主题", "width": 1600, "height": 900,
    "output": "01.png", "copy": {"headline": "已确认标题", "support": "", "cta": ""},
    "content_flags": {"text": true, "cta": false, "logo": false, "visual": true},
    "status": "planned", "tool": "", "actual_size": null,
    "reviewed_sha256": "", "review": {}, "brand_review": {}
  }]
}
```

这是结构示例，需要替换品牌路径和真实内容；不作为已确认需求。copy 可以增添合法说明、标签等命名字段，值均为字符串；无文字任务用 `{}`。每一交付文件对应一条 job，主题×尺寸仅按用户要求展开，样张计入总量。

brand_profile 相对 batch.json 解析，资料中的资产相对 profile.json 解析。profile_fingerprint 用 `profile_utils.py` 获取并填写，不能随意造值。恢复不兼容的旧任务时先显式迁移到当前 schema，保留原输出和确认依据，重审后再判通过。无品牌的项目也可使用只含项目标识与本次约束的资料包，见 [资料接入说明](brand-profiles.md)。

stage 为 concept 或 final；concept 可以使用 draft 资料和 proposed 的文案/规格。final 要求 ready 资料、copy_status 为 confirmed 或 authorized_draft、spec_status 为 confirmed，且 source 非空。authorized_draft 表示用户已经授权代拟，不是模型自行授权自己。审核通过的 concept 仍然是概念稿，不能声称可投放。

## 工具命令

Python 3.9+；图片检查/排版依赖 Pillow 9.1+（使用 Image.Resampling），计划检查只用标准库。这是接口下限，已测组合为 Python 3.9.6 / Pillow 11.3.0；未对所有中间版本逐一验证。优先使用现有运行时，缺依赖时说明并使用项目环境，不自动安装系统字体。

```bash
python3 /absolute/skill/scripts/profile_utils.py /absolute/brand/profile.json
python3 /absolute/skill/scripts/check_batch.py /absolute/batch.json --plan-only
python3 /absolute/skill/scripts/check_batch.py /absolute/batch.json
```

传例外时给 profile_utils.py 加 `--overrides /absolute/overrides.json`，内容为与 batch/layout 相同的数组。交付阶段在所有审核和实际文件检查通过后报告完成；不得为让检查通过伪造 review。

## 提示词

在本记录模式中，每个输出保存实际使用的提示词。固定块来自当前品牌与选定方向，可变块来自本 job；不要把其他品牌的颜色、人物禁令等硬塞进模板。

包含：用途与受众、核心信息及视觉创意、尺寸、图文关系与阅读路径、疏密与有目的的留白、字形层级和具体材质/图形处理、图片角色、当前品牌必须保留项、允许变化项、本张内容及精准文字（若由图像工具负责）、禁止改动项。精确后期模式明确底图不绘制后置文字/Logo/按钮，避免重复；一步生成模式则包含完整文案且如实核查精度。依当前工具规则执行，不编造 seed、字体加载等不存在的工具参数。

批次中断后先检查文件和资料指纹，保留未变且已通过的项目；不因恢复就重生成全部。用户仅要方案或技能更新，不执行此生图流程。

## 记录范围与分享

只保存恢复、核对文案和追踪修改所需的信息。当前授权项目中的完整文案和工作路径可以用于执行；不要在提示词/日志中附带与生成无关的内部文档全文、登录参数、凭据或个人信息。能用局部参考或脱敏示例表达主题时，不额外外传原始资料；必要内容确需交给外部服务但授权不明时先解决该缺口。

脚本生成的 batch/render 记录属于项目工作记录，可能包含完整文案和绝对路径，不默认公开分享。对外导出审核记录时另建副本，把路径改为相对路径，遮蔽不必要的个人信息、内部标识和访问参数；不改原始核验记录或沿用改动后的旧哈希。只分享用户要求的成品/记录，临时副本放当前任务目录，按用户保存要求处理，不擅自删除源资产。
