# 商品字段能力矩阵（Product Capability Matrix）

> **重要原则**：本文件提供字段能力的结构化参考矩阵，但**运行时必须以实际页面为准**。矩阵只能作为定位参考，不能覆盖页面事实。不同类目（美食、丽人、休闲娱乐、住宿等）的字段存在性、可编辑性差异很大，进入编辑页后必须先读取真实页面结构，生成字段能力快照，再建立修改计划。

## 矩阵字段定义

每个字段在矩阵中包含以下属性：

| 属性 | 说明 |
|---|---|
| `field` | 字段名称 |
| `category_scope` | 适用类目范围（当前页面实际类目） |
| `section` | 所属页面区域/步骤（如基础信息、价格与库存、商品内容、使用规则、资质与其他） |
| `capability` | 能力状态：`editable` / `readonly` / `derived` / `relation` / `absent` |
| `control_type` | 控件类型：`text_input` / `number_input` / `textarea` / `select` / `radio` / `checkbox` / `image_upload` / `file_upload` / `rich_text` / `relation_picker` / `display_only` |
| `validation` | 校验规则（数值范围、格式、字数限制等） |
| `operations` | 支持的操作：`set` / `increment` / `decrement` / `replace` / `append` / `remove` |
| `readback` | 回读方式：重新读取输入框值 / 读取商品详情展示值 / 读取关联弹窗已选项 |
| `dependencies` | 依赖字段（修改此字段可能影响的其他字段，或此字段依赖的其他字段） |

## 能力五态定义

| 状态 | 标识 | 含义 | 处理方式 |
|---|---|---|---|
| 可编辑 | `editable` | 页面存在直接输入控件，可直接修改 | 正常执行修改，写入后回读 |
| 只读 | `readonly` | 页面存在但为只读展示，无输入控件 | 明确告知商家不可修改，停止该字段 |
| 派生 | `derived` | 页面展示为计算/派生值，由其他字段计算得出 | 先定位来源字段，展示计算关系，修改来源字段间接变更 |
| 关联 | `relation` | 需通过独立关联流程/弹窗修改 | 走关联字段独立流程，不直接写入 |
| 缺失 | `absent` | 当前类目页面不存在该字段 | 停止并说明类目限制，不得声称可改 |

---

## 字段能力矩阵

### 一、基础信息

#### 1. 商品名称/标题

```yaml
field: 商品名称/标题
category_scope: 全类目
section: 基础信息
capability: editable
control_type: text_input
validation:
  max_length: 页面实际限制（通常 30-60 字）
  forbidden_words: ["最", "第一", "顶级", "全网最低", "国家级"]
operations:
  - set
readback: 重新读取输入框值
dependencies: []
```

#### 2. 商品类目

```yaml
field: 商品类目
category_scope: 全类目
section: 基础信息
capability: editable
control_type: select
validation:
  must_match: 平台类目树
operations:
  - set
readback: 重新读取类目选择器显示值
dependencies:
  - 类目变更后字段能力矩阵可能完全变化，需重新读取页面
```

#### 3. 商品主图（首图）

```yaml
field: 商品主图
category_scope: 全类目
section: 基础信息
capability: editable
control_type: image_upload
validation:
  format: ["jpg", "png"]
  min_count: 1
  real_material_required: true
operations:
  - replace
readback: 重新读取图片上传区域已上传图片
dependencies: []
```

> 素材要求：必须由商家提供真实拍摄图片，禁止生成虚构商品图。详见 [material-policy.md](material-policy.md)。

#### 4. 商品图片集（轮播图）

```yaml
field: 商品图片集
category_scope: 全类目
section: 基础信息
capability: editable
control_type: image_upload
validation:
  format: ["jpg", "png"]
  min_count: 页面实际要求（通常 3-5 张）
  real_material_required: true
operations:
  - replace
  - append
  - remove
readback: 重新读取图片上传区域已上传图片列表
dependencies: []
```

---

### 二、价格与库存

#### 5. 售卖价/团购价

```yaml
field: 团购价格/售卖价
category_scope: 全类目
section: 价格与库存
capability: editable
control_type: number_input
validation:
  positive: true
  precision: 整数或两位小数（以页面为准）
  min: 类目下限
  max: 类目上限
  price_relation: 售卖价不得高于原价
operations:
  - set
readback: 重新读取输入框值
dependencies:
  - 原价/划线价（价格关系校验）
```

#### 6. 原价/划线价/门市价

```yaml
field: 原价/划线价
category_scope: 全类目（多数类目）
section: 价格与库存
capability: derived
control_type: display_only
validation: {}
operations: []
readback: 读取页面展示值
dependencies:
  - 套餐内容/服务项目总价（原价由其计算得出）
```

> 处理方式：不直接修改原价展示值，需修改其来源字段（套餐内容/服务项目），修改后确认派生值已按预期更新。

#### 7. 库存数量

```yaml
field: 库存数量
category_scope: 全类目
section: 价格与库存
capability: editable
control_type: number_input
validation:
  integer: true
  min: 0
operations:
  - set
  - increment
  - decrement
readback: 重新读取输入框值
dependencies:
  - 库存模式（如有限库存/无限库存切换）
```

> 库存语义：库存表示**最终总库存**，不是新增库存。增量操作需先读原值再计算目标值。

#### 8. 限购规则

```yaml
field: 限购规则
category_scope: 全类目
section: 价格与库存
capability: editable
control_type: number_input 或 select（不限）
validation:
  positive_integer: true
  or_value: "不限"
operations:
  - set
readback: 重新读取输入框/选择器值
dependencies: []
```

---

### 三、商品内容

#### 9. 套餐内容/商品规格

```yaml
field: 套餐内容/商品规格
category_scope: 全类目
section: 商品内容
capability: editable
control_type: textarea 或 rich_text
validation:
  forbidden_words: ["最", "第一", "顶级", "全网最低", "国家级"]
operations:
  - set
  - append
readback: 重新读取输入框/富文本编辑器值
dependencies:
  - 原价/划线价（套餐内容变更可能影响派生的划线价）
```

#### 10. 商品详情/图文详情

```yaml
field: 商品详情/图文详情
category_scope: 部分类目（美发等类目为 absent）
section: 商品内容
capability: editable 或 absent
control_type: rich_text
validation:
  forbidden_words: ["最", "第一", "顶级", "全网最低", "国家级"]
operations:
  - set
  - append
readback: 重新读取富文本编辑器值
dependencies: []
```

#### 11. 商品标签/卖点

```yaml
field: 商品标签/卖点
category_scope: 部分类目（美发等类目为 absent）
section: 商品内容
capability: editable 或 absent
control_type: text_input 或 tag_selector
validation:
  max_count: 页面实际限制
  forbidden_words: ["最", "第一", "顶级", "全网最低", "国家级"]
operations:
  - set
  - append
  - remove
readback: 重新读取已选标签列表
dependencies: []
```

---

### 四、使用规则

#### 12. 可用时间

```yaml
field: 可用时间/使用时间
category_scope: 全类目
section: 使用规则
capability: editable
control_type: checkbox_group 或 time_range_picker
validation: {}
operations:
  - set
readback: 重新读取已选项
dependencies: []
```

#### 13. 使用有效期

```yaml
field: 使用有效期
category_scope: 全类目
section: 使用规则
capability: editable
control_type: date_range_picker 或 number_input（天数）
validation:
  reasonable_range: true
operations:
  - set
readback: 重新读取日期/数值
dependencies: []
```

#### 14. 适用门店

```yaml
field: 适用门店
category_scope: 全类目
section: 使用规则
capability: relation
control_type: relation_picker
validation:
  must_exist: 商家名下有效门店
operations:
  - set
readback: 读取关联弹窗已选门店列表
dependencies: []
```

> 处理方式：走独立关联流程，在门店选择弹窗中操作，不直接写入。

#### 15. 预约规则

```yaml
field: 预约规则/预约要求
category_scope: 全类目
section: 使用规则
capability: editable
control_type: radio 或 select
validation: {}
operations:
  - set
readback: 重新读取已选项
dependencies: []
```

#### 16. 退款规则

```yaml
field: 退款规则
category_scope: 全类目（多数类目）
section: 使用规则
capability: readonly
control_type: display_only
validation: {}
operations: []
readback: 读取页面展示值
dependencies: []
```

> 处理方式：多数类目仅展示不可编辑，告知商家不可修改。

---

### 五、资质与其他

#### 17. 行业资质

```yaml
field: 行业资质
category_scope: 部分类目（美发等类目为 absent）
section: 资质与其他
capability: editable 或 absent
control_type: file_upload
validation:
  format: ["jpg", "png", "pdf"]
  real_material_required: true
operations:
  - replace
readback: 重新读取已上传文件列表
dependencies: []
```

> 素材要求：必须由商家提供真实资质文件，禁止生成或伪造资质。详见 [material-policy.md](material-policy.md)。

#### 18. 商品资质

```yaml
field: 商品资质
category_scope: 部分类目（美发等类目为 absent）
section: 资质与其他
capability: editable 或 absent
control_type: file_upload
validation:
  format: ["jpg", "png", "pdf"]
  real_material_required: true
operations:
  - replace
readback: 重新读取已上传文件列表
dependencies: []
```

#### 19. 客服电话

```yaml
field: 客服电话
category_scope: 部分类目（美发等类目为 absent）
section: 资质与其他
capability: editable 或 absent
control_type: text_input
validation:
  phone_format: true
operations:
  - set
readback: 重新读取输入框值
dependencies: []
```

---

## 类目能力差异速查

| 字段 | 美食/餐饮 | 丽人/美发 | 休闲娱乐 | 住宿 |
|---|---|---|---|---|
| 商品名称/标题 | editable | editable | editable | editable |
| 商品主图 | editable | editable | editable | editable |
| 商品图片集 | editable | editable | editable | editable |
| 团购价格/售卖价 | editable | editable | editable | editable |
| 原价/划线价 | derived | derived | derived | derived |
| 库存数量 | editable | editable | editable | editable |
| 限购规则 | editable | editable | editable | editable |
| 套餐内容/规格 | editable | editable | editable | editable |
| 商品详情/图文详情 | editable | absent | editable | editable |
| 商品标签/卖点 | editable | absent | editable | editable |
| 可用时间 | editable | editable | editable | editable |
| 使用有效期 | editable | editable | editable | editable |
| 适用门店 | relation | relation | relation | relation |
| 预约规则 | editable | editable | editable | editable |
| 退款规则 | readonly | readonly | readonly | readonly |
| 行业资质 | editable | absent | editable | editable |
| 商品资质 | editable | absent | editable | editable |
| 客服电话 | editable | absent | editable | editable |

## 使用说明

1. 本矩阵为**参考定位工具**，运行时必须以实际页面控件为准。
2. 进入编辑页后，先对商家诉求涉及的字段逐一判定实际能力状态，生成字段能力快照。
3. 如实际页面与矩阵不一致，以实际页面为准，并记录差异。
4. 类目变更后，字段能力矩阵可能完全变化，必须重新读取页面。
5. 图片/资质类字段的素材来源和合规性判定，详见 [material-policy.md](material-policy.md)。
6. 商家口语到字段的映射，详见 [product-fields.md](product-fields.md)。
