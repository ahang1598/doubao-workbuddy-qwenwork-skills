---
name: foreign-legal-english-term-precision
name_en: foreign-legal-english-term-precision
description: Use when translating, reviewing, or drafting legal English where a Chinese or English legal term must be chosen by legal role, forum, procedure, jurisdiction, or document function rather than by dictionary meaning; especially for courtroom actors, parties, counsel, witnesses, court staff, and document-wide terminology consistency.
---
# Foreign Legal English Term Precision

## R - Reading

Scope signals:

- Compare exact meanings across PRC law and common-law usage before choosing terms.
- Covers courtroom actor terms including plaintiff, defendant, public defender, guardian ad litem, fact-finder, juror, judge, party, witness, and clerk.

## I - Interpretation

Treat legal English term choice as a controlled legal judgment, not as word lookup. First identify the legal domain, legal system, procedural posture, and function of the actor or concept. Then choose the term that matches that function, and explicitly reject close but wrong alternatives.

For courtroom actors, the central question is not “这个中文怎么翻译”, but “此人在此程序中承担什么身份”. For example, plaintiff, claimant, complainant, applicant, petitioner, defendant, accused, respondent, party, litigant, client, witness, judge, juror, and fact-finder mark different procedural relationships.

## A1 - Past Application

Key near-synonym distinctions:

- plaintiff/claimant/complainant depend on civil, arbitration, complaint, or criminal-report context.
- defendant/accused/respondent depend on civil defendant, criminal accused, or appeal/administrative response context.
- party/litigant/client cannot be swapped without checking whether the person is a procedural party, a litigant, or a lawyer's client.
- judge/juror/fact-finder require checking whether the decision maker decides law, fact, or both.

## A2 - Future Trigger

Invoke this skill when the user asks for legal English translation, bilingual drafting, review, or terminology consistency and the task contains:

- legal roles or courtroom actors;
- ambiguous party labels;
- a need to choose between multiple accepted English terms;
- mixed Chinese law, common law, Hong Kong, U.S., U.K., arbitration, administrative, civil, or criminal contexts;
- a request like “这个词用哪个更准确”, “审一下术语”, “统一法律英语表达”.

Do not invoke for ordinary vocabulary, non-legal English polishing, or a request that only asks for a general explanation without translation or drafting consequence.

## E - Execution

1. Locate the legal setting: civil, criminal, administrative, arbitration, company, contract, tort, regulatory, or extraterritorial.
2. Locate the role/function: party, representative, lawyer, witness, decision maker, court staff, right holder, obligor, regulator, defendant, accused, respondent, etc.
3. Locate the legal system: PRC, U.S., U.K., Hong Kong, EU, civil law, common law, international law.
4. Choose the term and list 1-3 rejected alternatives with reasons.
5. Check consistency across the document: same function uses same term; changed function uses changed term.
6. Output in this format: recommended term; context condition; rejected terms; drafting note.

## B - Boundary

This skill does not decide the merits of a case, identify binding law, or replace jurisdiction-specific legal research. If the issue is primarily about litigation procedure, civil-law doctrine, criminal elements, corporate finance, or extraterritorial regulation, call the relevant related skill after this general term check.

## Related Skills

- `procedure-litigation-term-mapper`: for procedure-stage and court-document terms.
- `civil-law-private-rights-translator`: for civil/private-law doctrine terms.
- `criminal-law-elements-offenses-translator`: for offense, element, and criminal responsibility terms.
- `extraterritorial-rule-of-law-translator`: for long-arm, sanctions, blocking statute, and sovereignty terms.

## Audit

- Distillation: merged closely related courtroom-role rules into one broader precision checker.
- Quality gates: V1/V2/V3 passed in `../verified.md`.
