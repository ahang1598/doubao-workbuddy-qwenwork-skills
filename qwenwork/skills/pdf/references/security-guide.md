# Security Guide

## Encryption Standards

PDF encryption is handled by `secure_pdf.py`. pypdf uses AES-256 (PDF 2.0)
when available, falling back to AES-128 (PDF 1.7).

### Password roles

| Password type | What it controls |
|---|---|
| User password | Required to open and read the PDF |
| Owner password | Required to change permissions, print in high quality |

If only `--owner-password` is set, users can open the file without a password
but cannot modify permissions.

### Strong passwords

- Minimum 12 characters
- Mix letters, numbers, symbols
- Do not reuse the user and owner passwords

---

## Redaction

`secure_pdf.py --action redact` adds black box annotations over matched text.

### Built-in pattern names

| Pattern name | What it matches |
|---|---|
| `SSN` | US Social Security Numbers (123-45-6789) |
| `email` | Email addresses |
| `phone` | US phone numbers |
| `credit_card` | 16-digit credit card numbers |
| `ip_address` | IPv4 addresses |

### Custom patterns

Use Python regex syntax with `--custom-pattern`:

```bash
python scripts/secure_pdf.py --action redact \
    --input report.pdf --output redacted.pdf \
    --custom-pattern "ACME-\d{6}" "Employee #\d+"
```

### Important limitation

This implementation uses **annotation-based redaction** (black boxes drawn
over text). The underlying text remains in the PDF stream. For court-admissible
or legally required redaction, use a tool that permanently removes content
from the PDF stream (e.g., Adobe Acrobat's Redact tool, or `qpdf --qdf` with
manual stream editing).

For most internal document workflows, annotation redaction is sufficient.

---

## Metadata Privacy

PDF files can contain sensitive metadata: author name, company, creation tool,
filesystem paths embedded in XMP metadata.

Strip metadata before sharing externally:

```bash
python scripts/secure_pdf.py --action strip-metadata \
    --input internal_draft.pdf --output clean_for_sharing.pdf
```

Alternatively, combine with optimize:

```bash
python scripts/optimize_pdf.py draft.pdf clean.pdf --strip-metadata
```

---

## Permission Flags

pypdf's `encrypt()` does not expose granular permission flags in the current
API. For fine-grained permissions (print only, no copy, no annotations), use
`qpdf` directly:

```bash
# Allow printing only, block copy and modification
qpdf --encrypt "" "ownerpass" 256 \
     --print=full --modify=none --extract=n --annotate=n \
     -- input.pdf output.pdf
```

---

## Security Checklist for PDF Distribution

- [ ] Sensitive PII redacted before sharing
- [ ] Metadata stripped if document contains author/company info
- [ ] Encrypted with strong user password if content is confidential
- [ ] Owner password different from user password
- [ ] Output validated with `validate_pdf.py` after security operations
