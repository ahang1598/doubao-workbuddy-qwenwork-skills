# 待专家复核事项

本文件仅记录技术审查发现的规则衔接疑点，不给出替代条款，也不判断哪种法律方案正确。专家确认前，现有法律政策和默认参数保持不变。

## 1. 起草方与付款、验收角色

- 现有位置：`standard_policy.md` 第 5—8 行；`default-commercial-parameters.md` 的角色规则；`default-parameter-profiles.md` 第 27—29 行。
- 观察：标准政策将起草方表述为验收确认方和暂缓付款方，但参数资料同时提到起草方可能是收款方、供应方或服务方。
- 可能场景：供应商、服务商或无付款义务的保密协议由起草方起草。
- 请专家确认：本 Skill 是否仅服务付款方/需求方起草；如不是，验收权、付款救济与起草方身份应如何对应？

## 2. 普通责任上限的表达方向

- 现有位置：`default-commercial-parameters.md` 与 `evals/sample_contract.json`。
- 观察：规则资料出现“责任上限不低于合同含税总价”，样例正文使用“累计责任不超过合同含税总价”。
- 请专家确认：前者是否表达内部谈判底线、后者是否表达合同条款；自动起草和校验分别应采用什么语义？

## 3. standard_term 与 standard_parameter

- 现有位置：`deal-schema.md`、`default-parameter-profiles.md`、`draft-json-schema.md` 和 `standard_policy.md`。
- 观察：争议解决、书面验收、责任上限例外等内容在部分文件被视为标准风险条款，在参数 profile 中又作为必须覆盖项目。
- 请专家确认：这些项目是否允许在 profile 中以 `standard_parameter` 记录，还是应分别记录条款与数值参数？

## 4. 骨架与参数 profile 覆盖范围

- 现有位置：`skeleton_families.md`、`default-parameter-profiles.md` 和 `preflight.py`。
- 观察：保密协议、generic 及部分场景没有一一对应的参数 profile；当前样例通过 `not_applicable` 处理保密协议的验收项。
- 请专家确认：这些场景应建立专用 profile，还是继续允许按通用规则加逐项不适用说明？

## 5. 待核查事实的合同表达

- 现有位置：`deal-schema.md` 与 `draft-json-schema.md`。
- 观察：资料允许 pending 以条件、义务或可填写空白处理，并要求 aliases 与 forbidden_assertions 防止写成既成事实。
- 请专家确认：不同类型 pending（审批、权属、授权、登记）是否需要更细的标准处理模板或禁止表述清单？
