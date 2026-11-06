# 头像规范

## 一、两种放置方式

### 单专家（agent_template）

- 位置：`<expert_id>/avatars/<expert_id>.png`
- manifest 声明：`metadata.avatar: "avatars/<expert_id>.png"`
- 校验：`expert_store.validate_expert_package` 会检查文件存在 + 包内相对路径

### 专家团（agent_group）

- 位置：`<expert_id>/avatars/<leader_id_or_member_id>.png`
  （leader 固定 `avatars/leader.png`，成员 `avatars/<member>.png`）
- **无需 manifest 声明**：`agent_group.read_group_members` 隐式扫描
  `avatars/<id>.png`，存在则附绝对路径给前端

## 二、基本要求

| 项目 | 要求 |
|------|------|
| 格式 | PNG 优先，JPG 亦可 |
| 尺寸 | 512×512 正方形 |
| 体积 | 单张不超过 500KB |
| 风格 | 全套统一插画风，观感专业 |
| 内容 | 贴合角色设定，规避敏感元素 |

> 用 `image_gen` 出图，`size` 传 `"1024x1024"`——先出高清原图，展示端缩到 512×512。

## 三、生成策略

**单专家**：只需 1 张
- `avatars/<expert_id>.png`

**专家团**：leader 与每个成员各 1 张
- `avatars/leader.png` — 主理人
- `avatars/<member>.png` — 每位团员

---

## 四、Prompt 构建核心原则

**prompt 不套通用模板，一律参照该角色的 persona 正文。**

### 提炼路径

1. 通读该角色的 persona 文件
2. **定身份**：从标题与开篇得到职业画像
3. **挑特征**：从能力描述里选可视觉化的关键词（着装、道具、符号）
4. **定气质**：由工作风格与注意事项推出性格基调
5. **定人物属性**：据 name 判断性别与画风倾向

---

## 五、个人头像 Prompt 组装

```
[风格开场] + [身份主体] + [外观细节] + [神态] + [背景点缀] + [收尾规范]
```

| 段 | 作用 | 示例 |
|------|------|------|
| 风格开场 | 定下全局画风 | `Flat vector-style avatar illustration,` |
| 身份主体 | 一句话点出职业身份 | `a male data platform engineer,` |
| 外观细节 | 由能力推断着装与道具 | `dark hoodie, lanyard badge, holding a laptop with pipeline diagrams,` |
| 神态 | 由工作风格推断 | `calm, methodical look,` |
| 背景点缀 | 放入领域符号 | `faint node graphs and data pipelines behind,` |
| 收尾规范 | 固定句式 | `Upper body, front facing. Plain light background. Sharp, clean, professional.` |

### 示例 1：数据平台工程师

persona 要点：角色=数据平台工程师，能力=流水线搭建、任务调度与监控，输出=稳定的数据链路

```
Flat vector-style avatar illustration, a male data platform engineer,
dark hoodie, lanyard badge, holding a laptop showing pipeline diagrams,
calm, methodical look,
faint node graphs and data pipelines in the background.
Upper body, front facing. Plain light background. Sharp, clean, professional.
```

### 示例 2：跨境财税顾问

persona 要点：角色=跨境财税顾问，能力=多国税务规则、汇率与申报流程

```
Flat vector-style avatar illustration, a female cross-border tax advisor,
neat blazer, holding a tablet with world map and tax flow charts,
poised, detail-minded expression,
soft globe and ledger motifs in the background.
Upper body, front facing. Plain light background. Sharp, clean, professional.
```

---

## 六、团队风格统一规则

团队全套头像必须共用同一组**风格锚定词**：

**每条 prompt 的固定开场：**

```
Flat vector-style avatar illustration, unified series style with even lighting and minimal shadows,
```

**每条 prompt的固定收尾：**

```
Upper body, front facing. Plain {tone} background. Sharp, clean, professional.
```

### 背景底色（建议，非强制）

| 领域 | 参考底色 |
|------------|---------|
| 技术工程 | 靛蓝冷调 |
| 数据智能 | 青碧浅底 |
| 内容创作 | 奶油暖黄 |
| 金融投资 | 藏蓝衬金 |
| 医疗健康 | 薄荷浅绿 |
| 教育培训 | 天青浅底 |

> 同一团队的全套头像锁定**同一种**底色，保证系列协调感。

---

## 七、执行流程

1. **逐个读 persona** — 每个角色一份，作为唯一取材来源
2. **提炼要点** — 抽出可视觉化的身份与能力关键词
3. **写个人 prompt** — 按第五节公式逐段组装
4. **统一锚定** — 团队场景下，开场句与底色全域一致
5. **调用 image_gen** — 逐张出图到 `avatars/`，`size` 为 `"1024x1024"`
6. **重命名** — 单专家 `<expert_id>.png`；团 leader 用 `leader.png`，成员用 `<member>.png`
7. **核对** — 确认 `avatars/` 下文件齐全
8. **补声明** — 单专家在 `metadata.avatar` 写入相对路径（专家团免声明，靠隐式扫描）

## 八、注意事项

1. **取材于 persona**：prompt 必须源自 persona 内容，拒绝万能模板
2. **系列一致**：团队全套共用同一画风与底色
3. **取景克制**：只取头肩、面向前方，背景干净
4. **画面无字**：头像内不出现任何文字、logo、水印
5. **失败降级**：出图失败时在 README.md 登记缺图与建议 prompt，流程不中断

## 九、替换

用户可手动换成自定义头像，只需满足文件名、尺寸、格式三项规格：
- 单专家替换后无需改 manifest（声明路径不变）
- 专家团替换后被 `read_group_members` 自动拾取（隐式扫描）
