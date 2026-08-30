---
name_en: "cn-family-debt-ledger"
name: "家庭债务与责任账本"
displayName: "家庭债务与责任账本"
description: "识别家庭债务的债权人、名义债务人、用途、共同意思、资金流、担保、对外责任、内部承担和清偿路径。"
description_en: "Analyze family debts by creditor, nominal debtor, purpose, mutual intent, fund flow, security, external liability, internal allocation, and repayment path."
argument-hint: "请提供债务清单、合同或借据、资金流水、用途、担保和现有清偿情况。"
argument-hint-en: "Provide the debt list, contracts or IOUs, fund flows, purposes, security, and repayment status."
user-invocable: true
---

# 家庭债务与责任账本

读 [统一作业标准](../../references/operating-standard.md)、[结构化底稿](../../references/data-contracts.md) 和 [法律权威核验](../../references/authority-baseline.md)。

## 债务范围

覆盖银行贷款、房贷车贷、消费贷、经营借款、股东/关联方借款、亲友借款、信用卡、担保、税费、未付款合同、对子女或老人的持续费用、或有债务和未决争议。

## 三层判断

每项债务分别回答：

1. 对外是否可能由一方或双方承担；列明共同签名、追认、家庭日常需要、共同生产经营、债权人认知、用途和资金受益。
2. 双方内部如何分担、清偿和追偿；内部约定不得伪装成对债权人的当然免责。
3. 如何实际取得债权人同意、变更借款人、解除担保、涂销抵押或取得结清/释放文件。

按 [data-contracts.md](../../references/data-contracts.md) 建立 `debt_record`。对亲友借款、现金往来、倒签借据、关联方借款、循环转账和大额新增债务强化真实性与用途核查。

## 输出

债务总表、证据与资金流、对外责任暂定分析、内部承担方案、担保/抵押状态、债权人同意需求、清偿顺序、付款来源、追偿权、释放文件和待核实项。

任何“债务归一方，与另一方无关”的条款必须同时提示其通常仅约束双方内部，不能当然对抗未同意的债权人。发现伪造债务、逃债或损害债权人迹象时停止起草并升级律师。
