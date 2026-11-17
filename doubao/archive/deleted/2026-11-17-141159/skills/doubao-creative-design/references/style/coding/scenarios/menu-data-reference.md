# 菜单数据与检查参考（按需读取）

配合 [菜单设计 Spec](menu-spec.md) 使用。本文件保存原有 menu-plan-v1 字段、示例与检查语义，供批量改价、数据驱动排版或复杂套餐引用；简单视觉设计无需填满这套结构。

**能力状态**：当前包内尚未核实到实现这些菜单专属检查的可执行程序。下文 error、warning、SHA-256、locked-facts 等描述属于约定，不能据此声称已经自动运行。使用外部检查器时记录真实入口与运行结果；没有工具时按 Spec 核对实际成品。保留字段语义不等于新增必交文件。

示例不承载真实营业事实；不得把演示价、来源或 planned 资产当作已核实数据。共同事实、字体、资产与交付协议仍以公共规范为准。

##### 独立锁定事实

可把用户已确认、不允许此次改变的值记录到独立文件，交给 `--locked-facts` 比对：

```json
{
  "facts": [
    {"pointer": "/items/0/item_id", "expected": "item-latte", "source": "用户确认菜品表第 2 行"},
    {"pointer": "/items/0/name", "expected": "拿铁", "source": "用户确认菜品表第 2 行"},
    {"pointer": "/items/0/pricing/options/0/amount", "expected": "28.00", "source": "用户确认菜品表第 2 行中杯价格"}
  ]
}
```

`pointer` 使用绝对 JSON Pointer；锁定值进行精确 JSON 比对，不执行表达式，也不自动解析 PDF、图片或表格。使用数组位置时同时锁定该位置的 ID；重排数组后根据原始资料更新路径，不能为消除错误改写 expected。获准改价时用新的确认资料建立新的锁定版本，保留变更依据。

锁定文件是人工提供的核验输入，不是来源真实性证明。未提供时，报告明确提示没有执行独立源值比对，事实 QA 仍需执行。

## 附录 A：品类计划字段与示例

### 最小计划示例

以下是虚构演示菜单的数据示例，不能作为真实商家的事实。JSON 为合法结构示例，制作时按真实任务替换内容；本示例示范少品项饮品图文方向；图片来源与样式仅为计划记录，未实际生成资产，不能用于声明素材已就绪。

```json
{
  "schema_version": "menu-plan-v1",
  "scene": "menu",
  "project": {
    "task_id": "menu-demo-01",
    "title": "演示咖啡单",
    "mode": "create",
    "content_context": "fictional_demo",
    "delivery_stage": "draft",
    "carrier": "single-sheet",
    "reading_context": "桌面近距离阅读",
    "languages": [
      "zh-CN"
    ],
    "currency": "CNY",
    "scope_item_ids": [
      "item-latte"
    ],
    "deliverables": [
      "单页菜单图片"
    ],
    "assumptions": [
      "示例菜品和价格为虚构演示"
    ]
  },
  "sources": [
    {
      "source_id": "src-demo",
      "status": "agent_generated",
      "description": "本示例获准创作的演示内容"
    }
  ],
  "categories": [
    {
      "category_id": "cat-coffee",
      "name": "咖啡",
      "item_ids": [
        "item-latte"
      ]
    }
  ],
  "items": [
    {
      "item_id": "item-latte",
      "name": "拿铁",
      "source_ref": "src-demo",
      "pricing": {
        "mode": "variants",
        "options": [
          {
            "option_id": "latte-medium",
            "label": "中杯",
            "amount": "28.00",
            "unit": "杯",
            "display_text": "28"
          },
          {
            "option_id": "latte-large",
            "label": "大杯",
            "amount": "32.00",
            "unit": "杯",
            "display_text": "32"
          }
        ]
      }
    }
  ],
  "units": [
    {
      "unit_id": "page-01",
      "unit_type": "page",
      "category_ids": [
        "cat-coffee"
      ],
      "item_ids": [
        "item-latte"
      ],
      "reading_mode": "comparison",
      "layout": {
        "reference": "MN-L06",
        "description": "独立饮品插画与菜名成组，下方中杯大杯规格价格明确对齐"
      },
      "visible_text_refs": [
        "text-category",
        "text-columns",
        "text-latte"
      ]
    }
  ],
  "visual_brief": {
    "intent": "安静、清楚的咖啡单，留白围绕价格比较区展开",
    "typography_roles": "分类名突出，菜名清晰，中大杯价格等权",
    "color_roles": "暖白背景，深色文字，一种分类强调色",
    "image_policy": "图文结合，独立饮品插画与规格价格表相邻，纸感底面承托准确文字",
    "container_policy": "无卡片，以列对齐和留白分组"
  },
  "text_bindings": [
    {
      "text_id": "text-category",
      "entity_id": "cat-coffee",
      "field": "name",
      "text": "咖啡"
    },
    {
      "text_id": "text-columns",
      "entity_id": "item-latte",
      "field": "pricing.options.label",
      "text": "中杯 / 大杯"
    },
    {
      "text_id": "text-latte",
      "entity_id": "item-latte",
      "field": "name + pricing.options.display_text",
      "text": "拿铁 28 / 32"
    }
  ],
  "text_contract": {
    "render_text": [
      "咖啡",
      "中杯 / 大杯",
      "拿铁 28 / 32"
    ],
    "planning_text": [
      "菜名左列，规格价格各自成列"
    ],
    "metadata_text": [
      "menu-demo-01"
    ],
    "visible_text_projection": "render_text"
  },
  "validation_targets": [
    "MENU-PRICE-001",
    "MENU-COVER-001",
    "MENU-READ-001"
  ],
  "open_issues": [],
  "visual_strategy": {
    "image_mode": "illustrated",
    "reference_templates": [
      "MN-S01"
    ],
    "selection_reason": "用独立杯型图帮助辨认饮品，并清楚比较规格价格",
    "featured_item_ids": [
      "item-latte"
    ],
    "image_assignments": [
      {
        "item_id": "item-latte",
        "visual_role": "item",
        "image_id": "image-latte"
      }
    ]
  },
  "asset_plan": [
    {
      "asset_id": "asset-latte",
      "role": "dish_illustration",
      "production": "image_generate",
      "source_ref": "src-demo",
      "version": "planned-v1",
      "replacement_entry": "独立饮品插画槽位",
      "status": "planned"
    }
  ],
  "images": [
    {
      "image_id": "image-latte",
      "asset_id": "asset-latte",
      "role": "dish_illustration",
      "item_ids": [
        "item-latte"
      ],
      "source_ref": "src-demo",
      "unit_ids": [
        "page-01"
      ]
    }
  ]
}
```

### 字段与条件模块

核心字段为 `project`、`sources`、`categories`、`items`、`units`、`visual_brief`、`text_bindings`、`text_contract`、`validation_targets`、`open_issues`。无分类的菜单可使用一个不显示标题的逻辑组，增加 `show_heading: false`，不要为满足字段新增可见分类名。

| 字段／模块 | 约定与触发条件 |
|---|---|
| `project.mode` | `create / content-update / reprice / redesign / adaptation` |
| `project.content_context` | `real_business / fictional_demo` |
| `project.delivery_stage` | `draft / final`，真实营业终稿不能保留价格占位或未确认营业事实 |
| `project.carrier` | `single-sheet / booklet / folded / wall-board / mobile-static / interactive / custom` |
| `project.scope_item_ids` | 本次需要展示的菜品集合；套餐内部组件可不在此集合中 |
| `project.physical_spec` | 印刷或墙面任务记录尺寸、单位及已知制作条件；每项区分提供、确认或假设状态 |
| `project.display_spec` | 数字任务记录目标显示尺寸和阅读方式；交互任务另记实现范围 |
| `items[].translations` | 多语言时使用语言键值映射，并记录 `translation_status` 与待核对项 |
| `items[].description / tags` | 内容存在才启用；事实标签需有来源，图例通过 ID 关联 |
| `items[].field_sources` | 一个条目的价格、描述等来源不同时，按字段路径覆盖默认 `source_ref` |
| `items[].pricing` | `fixed/from` 使用 `amount`；`variants` 使用 `options`；`market` 使用 `display_text`；`included` 使用 `package_ref`；`pending` 使用 `missing_fields`；其他模式按 §2.3 |
| `items[].pricing.currency` | 默认继承项目币种，不同时显式覆盖并在展示中区分 |
| `packages` | 套餐存在时启用，结构见下文 |
| `images` | 有图时记录 `image_id`、公共 `asset_id`、`role`、`item_ids`、`source_ref`；示意图追加 `disclosure_text` 与显示位置 |
| `notices` | 有适用规则时记录 `notice_id`、准确文案、来源、适用菜品／分类／全局范围及展示单元 |
| `legends` | 有符号时记录 `legend_id`、准确含义、符号引用和出现单元；条目标签引用同一 ID |
| `units[].repeated_item_reasons` | 跨单元重复菜品时记录菜品 ID 与重复原因；共享源数据 |
| `units[].continued_from` | 连续分类或条目需要显式续接时引用前一单元 |
| `units[].reading_mode` | `lookup / comparison / package-choice / sequence / custom` |
| `units[].constraints` | 按需记录折线、装订、远读、裁切、长文本和交互约束 |
| 公共资产与生产字段 | 按选定 workflow 写入 Brief／HTML 实现；引用现有字体、资产、图层及生产契约 |

套餐结构：

```text
packages[]:
  package_id: 稳定 ID
  menu_item_id: 作为套餐入口的菜品 ID，其 pricing 保存套餐基础价格
  fixed_components[]: {item_id, quantity}
  choice_groups[]:
    group_id: 稳定 ID
    label: 准确组名
    min_select: 非负整数
    max_select: 不小于 min_select 的整数
    options[]: {choice_id, item_id, quantity, surcharge_amount}
  notice_ids: 适用说明引用
```

第一版套餐选项不重复选择同一 `choice_id`，数量由 `quantity` 表达；若真实业务支持重复选择，先扩展明确的数据语义，不能用重复 ID 模拟。`surcharge_amount` 是在基础套餐价上增加的金额，币种继承套餐入口；禁止套餐递归包含自身。内部组件可被多个套餐引用，`included.package_ref` 只用于明确从属于一个套餐的组件。

`text_bindings` 是菜单实体到可见文案的追溯记录，`field` 为说明性字段路径，不是可执行表达式。`text` 必须能在 `render_text` 找到；实际文字可以按排版拆分为多个 TEXT，但不能改写事实。QA 检查只能核对明确绑定和源数据，不声称已自动证明任意自然语言改写保持等义。

### 可执行接口补充

以下约定补齐条件字段的具体形状，避免规划与 QA 各自解释：

- 所有实体、规格、可选组和选项 ID 在计划内唯一。数组中的同一引用不重复；重复展示通过不同单元表达。
- `project.languages` 第一项是 `name` 的主语言；其余语言使用 `items[].translations`，`translation_status` 为 `pending / confirmed`。
- `physical_spec / display_spec / custom_spec` 使用 `{size: "带单位的尺寸说明", status: "provided | confirmed | assumed"}`，可追加制作条件。交互菜单的 `display_spec` 另有 `implementation_scope`。草稿缺规格输出 warning，终稿缺规格输出 error；尺寸可读性仍由 QA 验证。
- `fixed / from` 的价格记录 `amount / unit / display_text`；`variants` 每个选项记录 `option_id / label / amount / display_text`，单位按实际需要记录。`unavailable` 记录 `display_text / display_policy`。不适用的 `amount / options` 不保留，避免模式切换后的旧价格残留。
- `tags` 是图例 ID 数组。`legends[]` 为 `{legend_id, text, symbol_ref, source_ref, unit_ids}`。`symbol_ref` 是供渲染与人工核对的符号说明或资产引用，计划 QA 不验证外部符号文件。
- `notices[]` 为 `{notice_id, text, source_ref, scope, unit_ids}`；`scope` 使用 `{type: "global"}` 或 `{type: "items | categories", ids: [...]}`。品牌标题、币种说明等独立可见文案也可作为全局说明绑定，不虚构菜品来容纳文案。
- `images[].disclosure_unit_ids` 保存示意标识所在单元；`disclosure_text` 进入可见文案。图像的 `asset_id` 引用本计划公共 `asset_plan` 条目；公共资产的完整生产契约仍由原工作流验证。
- `units[].repeated_item_reasons` 是 `{菜品ID: "重复原因"}` 对象，在后续出现单元记录；缺少原因输出 warning。
- `open_issues[]` 为 `{message, status: "open | resolved", blocks_final: true | false}`；营业终稿仍有阻塞项则输出 error，草稿未解决项输出 warning。
- `text_bindings` 支持菜品、分类、套餐、说明、图例和图片实体。所有 `render_text` 有绑定，所有绑定有单元引用；每个页面展示的菜品有页面内文案绑定。直接 `name / text` 绑定可精确比对，复合绑定仍需 QA 核对，不能用包含任意一段文本证明整个条目完整。
- 可选 `--locked-facts` 文件由原始确认资料建立，结构为 `{facts: [{pointer, expected, source}]}`；`pointer` 为绝对 JSON Pointer，`expected` 为精确锁定值。使用边界见本文件开头及菜单 Spec 第六章。

### QA 检查接口

以下编号由菜单 QA 和计划 QA 共同使用，规则依据见菜单 Spec 第六章，本文件保留字段与检查编号。结构检查结果与成品 QA 结果分别记录。

| 检查 ID | 检查目标 | 结构检查范围 | 实际成品 QA |
|---|---|---|---|
| `MENU-STRUCT-001` | 结构可解析，条件字段齐备 | 版本、类型、枚举、条件字段 | 载体与真实需求一致 |
| `MENU-REF-001` | 关系引用有效 | ID 唯一、引用存在、套餐不递归 | 图片和说明在画面上归属正确 |
| `MENU-FACT-001` | 准确内容有来源 | 来源引用、已提供锁定值的比对、未解决项 | 逐项核对名称、标签、说明和译文 |
| `MENU-PRICE-001` | 菜品、规格、价格一致 | 金额格式、计价模式、规格归属、币种和源值 | 不错行、不跨栏误读，单位明确 |
| `MENU-PACK-001` | 套餐规则可理解且有效 | 数量范围、候选数量、加价和组件引用 | 固定项、可选项、加价能被区分 |
| `MENU-COVER-001` | 交付内容没有遗漏 | 范围内菜品覆盖，重复用途记录 | 没有裁掉、遮住或排出画面的内容 |
| `MENU-TEXT-001` | 可见文案可追溯 | text_bindings 与 render_text 对应 | 实际成品未混入规划文案，文字准确 |
| `MENU-IMAGE-001` | 图像身份和用途明确 | 资产引用、菜品关联、示意记录 | 菜品特征、数量和图片对应可信 |
| `MENU-READ-001` | 可以完成点单任务 | 仅检查目标是否记录 | 实际尺寸下检索、比较、理解套餐 |
| `MENU-MEDIA-001` | 适配所选载体 | 相应载体规格是否记录 | 折叠、装订、远读、手机显示等检查 |

机器报告采用 `error / warning / manual_check`；人工检查采用 `pass / fail / not_applicable / pending`。待人工检查不能自动变成通过，计划结构通过也不能代替渲染和真实交付检查。

## 附录 B：可选检查记录示例

以下模板用于复杂任务或需要追踪多版本的项目；简单任务可在 Brief／HTML 实现 中保留同等证据，不要求额外交付报告。占位内容须替换为实际记录，模板本身不代表通过。

```json
{
  "report_version": "menu-qa-v1",
  "project_id": "menu-demo-01",
  "plan_sha256": "填写机器报告中的实际输入摘要",
  "automatic_report": "menu-validation.json",
  "reviewed_artifacts": [{"path": "menu.png", "version": "填写实际版本或文件摘要"}],
  "review_mode": "reviewer_walkthrough",
  "checks": [
    {
      "check_id": "MENU-PRICE-001",
      "object_ref": "page-01/item-latte",
      "status": "pending",
      "evidence": [],
      "observation": "尚未检查实际渲染",
      "repair": "取得目标尺寸成品后核对中杯与大杯价格",
      "blocks_final": true
    }
  ],
  "warning_dispositions": [],
  "delivery_decision": "pending_evidence"
}
```

## 附录 C：图文方向字段与机器检查边界

`visual_strategy` 为图文计划对象：`image_mode` 使用 `image-led / illustrated / mixed / text-led`；`reference_templates` 是模板 ID 或 custom 字符串数组；`selection_reason` 说明所选图文关系；`featured_item_ids` 为重点菜品；`image_assignments[]` 为 `{item_id, visual_role, image_id}`，visual_role 使用 `hero / category / item / package`。text-led 另有 `text_led_reason`，不强制图片数量。

`images[].unit_ids` 指向实际展示单元。图片关联菜品、计划重点菜、显示单元应一致。菜品图分配只能引用 dish_photo、dish_illustration 或 generated_dish_demo，atmosphere 与 decoration 不代替菜品图。

既有 menu-plan-v1 的记录约定：缺少 visual_strategy 时提示 warning 与人工判断，不拒绝既有合法无图计划。新增图文任务应记录该对象。已选择图文方向却没有菜品图或遗漏重点菜，草稿提示 warning，final 输出 error；引用不存在、归属错误始终 error。明确 text-led 原因时允许无图通过。

计划中的 asset_plan 不证明资产已生成。是否真实就绪、视觉比例、图文吸引力及参考风格还原由本文件的实际成品 QA 核对。新检查统一使用 `MENU-IMAGE-001`，不把风格编号、图片数量或背景层数改为审美硬指标。
