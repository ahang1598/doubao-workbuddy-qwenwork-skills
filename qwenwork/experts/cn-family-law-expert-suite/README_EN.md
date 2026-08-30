# Family Law Expert

Version: 1.2.1

This suite supports Mainland China family-law lawyers, law-firm teams, in-house counsel, and users acting under lawyer supervision. It provides a traceable workflow from safety screening and staged intake through facts, evidence, current-law research, option analysis, agreement drafting, implementation planning, document production, and final quality control.

## Included skills

- Orchestration, staged intake, and integrated legal consultation.
- Document and bank-statement evidence analysis, asset and title ledger, debt and liability ledger, and child parenting plan.
- Current statute research and relevant-case research.
- Six agreement workflows with embedded, configurable Chinese-language templates: prenuptial property, marital property, divorce, cohabitation, family property partition, and adult voluntary guardianship.
- Formal document generation and the final legal/document quality gate.

All 17 skills are user-invocable. The orchestrator is recommended for multi-stage matters; a specialist skill may be invoked directly for a narrow, well-defined request.

## Systems and fallback

No connector is mandatory in version 1.2.1, and the package does not include `.mcp.json`. It can work with user-authorized files and the document or public-web capabilities already available in QwenWork.

- If an official source cannot be reached, retain the search strategy, access limitation, and items requiring manual verification; do not invent a statute, case number, or local procedure.
- If OCR or visual review is unavailable, identify the affected pages and confidence limits; do not infer signatures, seals, or unreadable text.
- If DOCX/PDF generation is unavailable, provide a structured Markdown agreement and attachments, clearly marked as not render-verified.
- If an external system is not authorized, do not bypass authorization or claim a successful connection.

Before asking anything, the suite reuses facts already supplied in the prompt, conversation, or authorized files. Each QwenWork card question configures 2–4 choices; the platform appends its own Other field. A single prompt may contain up to four questions, questions may be multi-select, and the recommended choice appears first.

When the user asks only for a blank or quick template, the suite skips the full intake and research pipeline and immediately returns a prebuilt DOCX. A partially informed draft reuses supplied facts and leaves visible placeholders instead of delaying output for avoidable questions.

In QwenWork, DOCX verification uses the bundled OOXML structure and text validator. It must not invoke LibreOffice, `soffice`, `libreoffice_bridge.py`, or `pdftoppm`, and it must not retry with alternate Python commands or search application directories. If PDF or page-image QA is requested, deliver the validated DOCX first and disclose that visual conversion is unavailable in the current runtime.

Formal legal conclusions and signable agreements require substantive review and approval by a qualified Mainland China lawyer. The suite does not replace identity checks, conflict checks, notarization, registration, tax, valuation, medical, psychological, litigation, or other specialist work.
