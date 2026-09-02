# 输出接口 — CaseRecord IP 输出格式

> 版本：v3.0.0 | Phase 7 CaseRecord 更新的结构化数据定义
> 供下游技能（如 ip-infringement-litigation-strategy）消费

---

## 一、CaseRecord 著作权比对字段

Phase 7 将比对结果写入 CaseRecord 的 `copyright_analysis` 字段：

```json
{
  "copyright_analysis": {
    "skill_version": "3.0.0",
    "analysis_date": "2026-06-18",
    "work_type": "art",
    "claimed_rights": ["reproduction", "adaptation"],
    "overall_impression": {
      "initial_anchor": "高度相似",
      "initial_basis": "整体月桂叶造型与层叠排列高度一致",
      "post_stripping_adjustment": "维持高度相似",
      "adjustment_reason": "剥离后独创性表达层面仍有高度重合"
    },
    "originality_elements": {
      "public_domain": [
        {
          "element": "月桂叶的自然形态",
          "reason": "自然界植物的客观形态属于公共领域"
        }
      ],
      "scenes_a_faire": [
        {
          "element": "项链的基本链条结构",
          "reason": "项链链条是珠宝设计的题材必然配置"
        }
      ],
      "original_expression": [
        {
          "element": "月桂叶的非对称层叠排列+渐变密镶工艺",
          "originality_strength": "强",
          "protection_breadth": "宽",
          "basis": "该排列方式和工艺组合体现设计师独特取舍"
        }
      ]
    },
    "similarity_result": {
      "overall_layer": {
        "similarity": "中度相似",
        "description": "整体观感存在相似氛围，但存在差异"
      },
      "structure_layer": {
        "similarity": "高度相似",
        "points": [
          {
            "point": "叶片层叠排列顺序",
            "originality_strength": "强",
            "similarity_level": "高度相似",
            "similarity_nature": "common_choice",
            "evidence_value": "高",
            "basis": "排列顺序高度一致，属非必然创作选择"
          }
        ]
      },
      "expression_layer": {
        "similarity": "高度相似",
        "points": [
          {
            "point": "渐变密镶的具体宝石间距与角度",
            "originality_strength": "强",
            "similarity_level": "高度相似",
            "similarity_nature": "common_choice",
            "evidence_value": "高",
            "basis": "间距参数与角度高度一致"
          }
        ]
      },
      "error_copying_points": [
        {
          "error_type": "非常规标注",
          "location": "叶脉编号第3片跳号至第5片",
          "evidence_value": "极高",
          "basis": "原被告在同一位置存在相同的非常规编号跳号"
        }
      ],
      "substantial_similarity": true,
      "summary": "独创性表达层面存在高度相似，含1处共同错误"
    },
    "contact_assessment": {
      "causal_chain": {
        "temporal_possibility": "原告2023年6月首发，被告2024年9月上架，时序成立",
        "reasonable_access": "广泛传播（巴黎时装周+50万粉丝社交平台）→合理接触机会成立",
        "contact_feasibility": "同行业（珠宝设计/电商销售）→接触可行性高",
        "indirect_contact": "被告店铺曾关注原告品牌账号→间接链存在",
        "contact_level": "高"
      }
    },
    "interaction_tier": "A",
    "interaction_reasoning": "接触证据充分+实质性相似成立→侵权成立可能性高，原告举证完成",
    "defense_preview": {
      "independent_creation": "可能性低——共同错误（叶脉编号跳号）难以用独立创作解释",
      "fair_use": "不适用——被告为商业用途完整使用",
      "public_domain_origin": "不适用——相似点位于独创性表达层",
      "no_access": "不成立——接触因果链四阶均成立",
      "lawful_source": "待评估——被告可能主张素材来自第三方供应商，原告应考虑追加实际制造商为共同被告"
    },
    "conclusion": {
      "rights_analysis": [
        {
          "right": "reproduction",
          "right_name": "复制权",
          "legal_basis": "著作权法第10条第1款第5项",
          "claim": "原告主张被告复制其独创性表达",
          "elements_analysis": "复制权侵权需证明：作品受保护+被告复制了受保护表达",
          "fact_subsumption": "独创性表达高度相似+接触可能性高+情形A",
          "verdict": "侵权成立可能性高"
        },
        {
          "right": "adaptation",
          "right_name": "改编权",
          "legal_basis": "著作权法第10条第1款第14项",
          "claim": "原告主张被告改编其作品",
          "elements_analysis": "改编权侵权需证明：被告改变作品创作出具有独创性的新作品",
          "fact_subsumption": "被告在原告独创性表达基础上做了材质变更",
          "verdict": "侵权成立可能性中"
        }
      ],
      "overall_verdict": "情形A：接触充分+实质性相似成立，复制权侵权成立可能性高",
      "degraded": false
    }
  }
}
```

---

## 二、字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `skill_version` | string | 是 | 本技能版本号 |
| `analysis_date` | string | 是 | 分析日期 YYYY-MM-DD |
| `work_type` | enum | 是 | 作品类型（input-spec.md §2.4） |
| `claimed_rights` | array | 是 | 涉诉权利项枚举数组 |
| `overall_impression` | object | 是 | 整体观感锚定与反向验证 |
| `overall_impression.initial_anchor` | string | 是 | 初始直觉分（高度/中度/弱/不相似） |
| `overall_impression.post_stripping_adjustment` | string | 是 | 反向验证后的修正结论 |
| `originality_elements` | object | 是 | 独创性三层剥离结果 |
| `originality_elements.original_expression[].protection_breadth` | string | 是 | 保护宽度（宽/中/窄） |
| `similarity_result` | object | 是 | 逐层比对结果 |
| `similarity_result.*.points[].similarity_nature` | string | 是 | 相似性质（common_expression/common_choice/common_error） |
| `similarity_result.error_copying_points` | array | 否 | 错误复制识别结果（如存在） |
| `similarity_result.substantial_similarity` | boolean | 是 | 实质性相似是否成立 |
| `contact_assessment.causal_chain` | object | 是 | 接触因果链四阶评估 |
| `contact_assessment.causal_chain.contact_level` | enum | 是 | 接触等级（高/中/低） |
| `interaction_tier` | enum | 是 | 三阶交互情形（A/A'/B/C） |
| `interaction_reasoning` | string | 是 | 三阶交互判定理由 |
| `defense_preview` | object | 是 | 被告抗辩路径预判 |
| `conclusion` | object | 是 | 综合分析结论 |
| `conclusion.rights_analysis` | array | 是 | 分权论证数组 |
| `conclusion.overall_verdict` | string | 是 | 综合判定 |
| `conclusion.degraded` | boolean | 是 | 是否降级输出 |

---

## 三、降级输出结构

当 `conclusion.degraded` 为 `true` 时，`conclusion` 结构调整为 C+D+G：

```json
{
  "conclusion": {
    "degraded": true,
    "preliminary_conclusion": "C: 基于现有信息，原告作品与被告素材在整体观感上存在一定相似性，但无法确认是否构成实质性相似",
    "degradation_note": "D: 缺少原始作品文件，仅基于文字描述进行定性分析；缺少被告素材的详细描述；错误复制识别受限",
    "supplement_advice": "G: 需补充原告作品原始文件、被告素材原始文件、接触线索（发表时间/传播范围/行业关系）以完成完整分析"
  }
}
```

---

## 四、下游消费说明

| 下游技能 | 消费字段 | 用途 |
|----------|----------|------|
| ip-infringement-litigation-strategy | `conclusion.rights_analysis` + `interaction_tier` | 制定诉讼策略 |
| copyright-remedy-compare | `similarity_result` + `contact_assessment` + `defense_preview` | 救济途径比较 |
| infringement-damages-calc | `conclusion.overall_verdict` | 损害赔偿计算 |

---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
