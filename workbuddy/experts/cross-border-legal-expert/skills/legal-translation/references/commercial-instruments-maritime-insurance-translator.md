---
name: commercial-instruments-maritime-insurance-translator
name_en: commercial-instruments-maritime-insurance-translator
description: Use when translating, reviewing, or drafting trade, negotiable-instrument, maritime, bill-of-lading, collision, salvage, or insurance-contract English where terms must match document function, transport risk, negotiability, carriage, indemnity, or marine/insurance law context.
---
# Commercial Instruments Maritime Insurance Translator

## R - Reading

Scope signals:

- Covers negotiable instrument, maritime transport, bill of lading, collision, marine salvage, and insurance contract.
- Bill of lading should be analyzed by document function, including receipt and carriage-related roles.
- Insurance contract is treated through indemnity and insurance-party structure.

## I - Interpretation

Trade, maritime, and insurance vocabulary must be translated by instrument function and risk allocation. A term may describe a transferable payment instrument, a transport document, evidence of receipt, a contract of carriage, a maritime incident, a salvage service, or an indemnity arrangement.

This skill asks what the document does, what risk or right it transfers, and which party bears or claims under it.

## A1 - Past Application

Commercial practice often links payment, carriage, title/documentary control, loss, rescue, and insurance coverage:

- negotiable instrument depends on negotiability and payment function.
- bill of lading may operate as receipt, evidence of carriage contract, and document connected with goods control.
- collision and marine salvage require maritime-law context, not ordinary accident/rescue wording.
- insurance contract requires insurer/insured, indemnity, coverage, and loss structure.

## A2 - Future Trigger

Invoke this skill for:

- letters, contracts, pleadings, policies, claims, or opinions involving negotiable instruments, bills of exchange, cheques, bills of lading, carriage of goods by sea, collision, salvage, hull/cargo insurance, indemnity insurance, life insurance, or insurance claims;
- review of trade finance or maritime documents where ordinary English words may hide legal functions.

Do not invoke for general corporate governance or securities terms unless the document also involves trade instruments or insurance/maritime risk.

## E - Execution

1. Identify the document/instrument: negotiable instrument, cheque, bill of exchange, bill of lading, policy, insurance contract, salvage agreement, claim notice.
2. Identify function: payment, transferability, receipt, carriage evidence, goods control, indemnity, coverage, salvage reward, liability allocation.
3. Identify parties: drawer, drawee, holder, carrier, shipper, consignee, insurer, insured, beneficiary, salvor.
4. Choose terms that preserve legal function instead of literal ordinary wording.
5. Flag ambiguous words that need document-function notes.
6. Output recommended term, functional reason, rejected alternatives, and risk note.

## B - Boundary

This skill does not decide coverage, liability, seaworthiness, title to goods, or negotiability as a legal conclusion. It supports terminology and drafting review. For company or securities issues, use `commercial-corporate-finance-translator`.

## Related Skills

- `commercial-corporate-finance-translator`: for broader commercial/company context.
- `civil-law-private-rights-translator`: for contract, liability, tort, and force majeure foundations.
- `foreign-legal-english-term-precision`: for party labels and consistency.

## Audit

- Distillation: retained as a separate compact skill because instrument/maritime/insurance terms share document-function and risk-allocation logic.
- Quality gates: V1/V2/V3 passed in `../verified.md`.
