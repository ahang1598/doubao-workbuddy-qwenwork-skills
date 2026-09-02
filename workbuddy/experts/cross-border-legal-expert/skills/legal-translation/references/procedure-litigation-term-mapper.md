---
name: procedure-litigation-term-mapper
name_en: procedure-litigation-term-mapper
description: Use when translating, reviewing, or drafting litigation/procedure English where terms must match procedural stage, court power, service method, evidentiary function, motion practice, decision type, or appellate posture; especially trial, prosecution, defense, service, jurisdiction, challenge, evidence, burden of proof, examination, motion, verdict, appeal, judgment, award, ruling, order, and determination.
---
# Procedure Litigation Term Mapper

## R - Reading

Scope signals:

- Check procedural terms against pre-trial, trial, and post-trial stages.
- Covers service, jurisdiction, evidence, burden of proof, motion, verdict, and appeal.
- Distinguish court decisions such as judgment, award, ruling, order, decision, and determination by forum and procedural effect.

## I - Interpretation

Procedure terms must be mapped to procedural function before translation. A word such as jurisdiction may refer to subject-matter power, personal jurisdiction, territorial jurisdiction, venue, national jurisdiction, or long-arm jurisdiction. A decision word may indicate a final judgment, arbitral award, procedural order, ruling on a point, or fact determination.

The skill converts procedural vocabulary into a stage-and-function map: who is acting, under what authority, at what stage, by what document, and with what legal effect.

## A1 - Past Application

Key procedural distinctions:

- trial is not merely “庭审”; it can mark the entire trial stage or adjudicative process.
- prosecution changes meaning between criminal prosecution, prosecuting agency, and act of bringing proceedings.
- service requires attention to service of process, service method, recipient, and proof of service.
- challenge may mean a juror challenge, objection, or recusal depending on target and procedure.
- verdict, judgment, award, ruling, and order are not interchangeable.

## A2 - Future Trigger

Invoke this skill when a task includes:

- bilingual pleadings, notices, judgments, arbitral materials, evidence lists, procedural orders, or appellate documents;
- terms about service, jurisdiction, evidence, burden, examination, motion, ruling, judgment, award, verdict, or appeal;
- a need to distinguish court litigation from arbitration, administrative proceedings, or criminal proceedings.

Do not invoke for purely substantive contract/corporate/civil-law terms unless procedure is central.

## E - Execution

1. Identify procedural track: civil, criminal, administrative, arbitration, enforcement, appeal, or cross-border service/jurisdiction.
2. Identify stage: pre-trial, trial, post-trial, appeal, enforcement, or review.
3. Identify actor and authority: court, arbitral tribunal, prosecutor, party, judge, jury, agency, or enforcement body.
4. Choose the procedure term by function: initiating, serving, proving, examining, moving, deciding, appealing.
5. Check decision type: final merits decision, procedural order, factual finding, legal ruling, arbitral award, jury verdict.
6. Output recommended term, rejected alternatives, and a short procedural reason.

## B - Boundary

This skill does not determine whether a court actually has jurisdiction, whether evidence is admissible, or whether an appeal is viable. It reviews terminology and drafting fit. For long-arm jurisdiction and extraterritorial application, hand off to `extraterritorial-rule-of-law-translator`.

## Related Skills

- `foreign-legal-english-term-precision`: for parties, counsel, court actors, and consistency.
- `criminal-law-elements-offenses-translator`: for prosecution/defense when offense elements matter.
- `extraterritorial-rule-of-law-translator`: for long-arm jurisdiction and cross-border regulatory reach.

## Audit

- Distillation: merged procedure-stage, service, jurisdiction, evidence, and decision-word candidates.
- Quality gates: V1/V2/V3 passed in `../verified.md`.
