# China Import Playbook

Read this file when mainland China is the import destination, goods will be stocked or sold in China, or the user asks about China Customs, CCC, GB standards, import VAT, Chinese labels, or China-market brand authorization.

## Official Source Routing

| Decision | Primary source | Verify |
|---|---|---|
| Customs declaration, supervision, valuation, origin, tariff classification, import restrictions | General Administration of Customs of the PRC, `https://www.customs.gov.cn/`, and China International Trade Single Window, `https://www.singlewindow.cn/` | Current rule or announcement, customs code, declaration elements, trade mode, transaction terms, dutiable value, origin, required permit, competent customs office |
| CCC catalogue, implementation rules, designated bodies, certificate status | Certification and Accreditation Administration of the PRC, `https://www.cnca.gov.cn/`, and the official certification-information query path linked by CNCA | Whether the exact product/model is in scope, rule number/version, applicant/manufacturer/factory, certificate status, covered model, issue/expiry/suspension status |
| Product quality, mandatory requirements, labels and market circulation | State Administration for Market Regulation, `https://www.samr.gov.cn/` | Applicable regulation, responsible entity, Chinese label/manual/warning, enforcement or recall notice |
| National standards | National Standard Full-text Disclosure System, `https://openstd.samr.gov.cn/` | Standard number, title, mandatory/recommended type, current status, publication/implementation date, replacement relationship, applicable clause |
| Import VAT and consumption tax policy | State Taxation Administration policy database, `https://fgk.chinatax.gov.cn/`, together with current customs collection rules | Taxpayer, current tax base and rate, customs-collected import VAT/consumption tax, effective date, special or transitional treatment |
| Customs IP protection | GACC customs IP protection records and current customs procedures | Recorded right, owner, goods/mark coverage, authorization and purchase chain; do not treat an overseas invoice as China-market distribution authorization |

Official source names or homepages are entry points, not conclusions. Record the exact page, rule, standard, query result, publication/effective date, and fields used. Recheck time-sensitive rules at execution time.

## China Import Sequence

1. Distinguish exporter/ship-from country from country of origin for every SKU.
2. Confirm the business model. Goods imported into a mainland warehouse for subsequent Tmall, JD, or own-site sales normally require analysis as commercial import and domestic circulation; do not select a retail-import model merely because the seller is an ecommerce company.
3. Resolve the importer/consignee, trade mode, transaction terms, invoice/packing-list fields, payment and logistics evidence.
4. Build candidate HS classifications from product material, function, construction, use, specifications, and official notes. Treat them as candidates until the authorized declarant/customs confirmation required by the task.
5. Check import restrictions, permits, CCC scope, current GB standards, product-specific safety rules, Chinese label/manual/warnings, and market-circulation requirements.
6. Check brand authorization, purchase chain, customs IP risk, and platform qualification separately. A purchase invoice may support title or transaction evidence but does not automatically prove China-market distribution authorization.
7. For batteries or dangerous goods, verify the exact SKU, battery cell/model, UN38.3, SDS/MSDS, battery declaration, packaging and booking classification separately. One model's file does not cover another model unless the document explicitly says so.
8. Calculate customs value, duty, import VAT, consumption tax when applicable, domestic charges, landed cost and unit cost from the task's authoritative inputs. Do not replace task-supplied rates or allocation rules.
9. Determine `可发运 / 条件放行 / 暂缓 / 禁止首批发运` per SKU and batch, with closing evidence and owner.

## Evidence Boundaries

- A foreign retail package does not prove compliance for sale in China.
- A CCC logo, certificate screenshot, or supplier statement does not prove that the exact model and factory are covered. Verify the official certificate record and scope.
- A standard number alone is insufficient. Verify that the standard is current and applicable to the exact product.
- Do not state that an item can be commercially imported or sold before required CCC, mandatory standard, label/manual, permit, dangerous-goods, and IP evidence is resolved.
- When the prompt supplies a governing calculation formula, rate, exchange rate, allocation rule, or deadline, use it as the task control and identify any conflict with an official rule instead of silently replacing it.
