---
name_en: "cn-family-asset-ledger"
name: "家庭财产与权属账本"
displayName: "家庭财产与权属账本"
description: "逐项梳理家庭财产的登记、出资、取得、控制、价值、负担、第三人权利、初步权属和拟约定结果。"
description_en: "Build an itemized family-asset and title ledger covering registration, funding, acquisition, control, value, encumbrances, third-party interests, and proposed allocation."
argument-hint: "请提供财产大类、登记情况、取得时间、出资来源、现值或估值材料及双方主张。"
argument-hint-en: "Provide asset categories, registration, acquisition timing, funding sources, value evidence, and each party's position."
user-invocable: true
---

# 家庭财产与权属账本

读 [统一作业标准](../../references/operating-standard.md)、[结构化底稿](../../references/data-contracts.md) 和 [法律权威核验](../../references/authority-baseline.md)。材料解析优先调用 `cn-family-document-evidence`。

## 覆盖范围

至少核对：不动产及预售/在建权益；车辆和登记动产；公司股权、股票、员工激励、代持、合伙和经营权益；存款、支付、证券、基金、理财和贵金属；公积金、养老金等权益；保险现金价值和受益安排；债权与合同权益；知识产权及收益；继承、赠与、父母出资、婚前积累和替代物；珠宝收藏、虚拟财产及其他经济权益。

## 逐项分析

对每项资产建立 `asset_record`，字段按 [data-contracts.md](../../references/data-contracts.md) 执行，并明确区分：

- 登记名义、实际控制、实际出资和资金来源。
- 婚前/婚后或同居阶段取得，继承赠与及赠与指向。
- 原物、孳息、自然增值、投资收益、替代物和混同。
- 按份/共同共有、共有人配偶、第三人权利、抵押查封租赁及处分限制。
- 当前法律性质的暂定分析与双方希望通过协议形成的结果。
- 价值基准日、估值方法、税费、所需同意、登记动作和失败替代。

## 输出规则

输出资产总表、权属争点、证据缺口、估值缺口、第三人/登记限制、拟分配结果、折价款和逐项履行表。账本可以提出初步权属分析，但不得把争议事实自动认定为确定权属；复杂股权、农村权益、信托、境外资产或重大税务必须升级专项复核。
