# Official Source Map

Use official or first-party sources before making high-risk statements about compliance, tax, IP, HS, tariff, customs, restricted products, or fulfillment.

## Source Priority

| Priority | Source type | Use for | Caveat |
|---:|---|---|---|
| 1 | Government customs, tariff, tax, regulator, and certification authority | HS/tariff, import restriction, VAT/GST/Sales Tax, certification, labeling, safety | Rules vary by country, state, and product category |
| 1 | Marketplace Seller Center, Seller University, Policy Center, or platform help | Prohibited/restricted products, listing approval, dangerous goods, FBA/warehouse constraints, appeals | Often requires login; without screenshots give verification path only |
| 1 | Official trademark, patent, copyright, and product safety databases | IP clearance signals, product recalls, live/dead trademark status, ownership | Search is not legal clearance |
| 2 | Official platform API/developer docs | Product tax code, order tax, customs, inventory, fulfillment, category fields | API fields are evidence fields, not final policy conclusions |
| 2 | Official carrier, postal, and 3PL docs | Dangerous goods, shipping restrictions, customs fields, phone/address/weight requirements | Carrier rules do not replace national law |
| 3 | Accio, WorkBuddy, third-party tools, customs brokers, competitor behavior | Candidate workflows, field checklists, HS/tariff candidates, operational ideas | Must be marked as non-official unless verified |

## Core Official Resources

| Judgment | Official resource | Fields to extract |
|---|---|---|
| China import declaration and clearance | General Administration of Customs of the PRC `https://www.customs.gov.cn/`; China International Trade Single Window `https://www.singlewindow.cn/` | Trade mode, consignee/importer, HS candidate, declaration elements, origin, transaction terms, dutiable value, permits, current announcement/rule and effective date |
| China CCC and certification | Certification and Accreditation Administration of the PRC `https://www.cnca.gov.cn/` and its official certification-information query path | Catalogue/rule version, exact product/model, applicant, manufacturer/factory, certificate status, scope and validity |
| China product regulation and labels | State Administration for Market Regulation `https://www.samr.gov.cn/` | Product-specific regulation, Chinese label/manual/warning, responsible entity, enforcement/recall notice |
| China national standards | National Standard Full-text Disclosure System `https://openstd.samr.gov.cn/` | Standard number/title, mandatory or recommended status, current/replaced/abolished status, implementation date, applicable clauses |
| China import VAT and consumption tax | State Taxation Administration policy database `https://fgk.chinatax.gov.cn/` together with current customs collection rules | Taxpayer, tax base, current rate, import VAT/consumption tax treatment, effective date and transitional rule |
| US import HS/tariff | USITC HTS `https://hts.usitc.gov/`; USITC Harmonized Tariff Information `https://www.usitc.gov/harmonized_tariff_information` | HTS code, chapter notes, statistical suffix, duty rate, revision date, additional duties |
| US customs classification cases | CBP CROSS `https://rulings.cbp.gov/home`; CBP Binding Ruling Program | Similar rulings, classification reasoning, material/use, origin, modified/revoked status |
| US export classification | US Census Schedule B `https://www.census.gov/foreign-trade/schedules/b/index.html` | Schedule B number, product description, version, obsolete-code status |
| EU customs tariff | EU TARIC `https://taxation-customs.ec.europa.eu/customs/common-customs-tariff-cct/tariff-classification-goods/eu-customs-tariff-taric_en`; Access2Markets | CN/TARIC code, measures, restrictions, antidumping, origin/destination |
| EU VAT / OSS / IOSS | European Commission VAT pages, Your Europe OSS, VIES VAT number check | VAT ID validity, OSS/IOSS path, B2B/B2C, destination-based VAT, Member State of Identification |
| US trademark/IP | USPTO Trademark Search, TSDR, ID Manual | Mark wording/design, live/dead status, goods/services, owner, related classes |
| TikTok Shop product policy | TikTok Shop Prohibited Products Policy, Restricted Products Policy, Listing/Product Policy | Prohibited vs restricted, qualification type, documentation, enforcement |
| Amazon policy and fulfillment | Amazon Seller Central restricted products, dangerous goods, FBA inventory/capacity, Manage Dangerous Goods Classification | Approval need, hazmat review, SDS/exemption sheet, FBA eligibility, IPI/capacity |
| Shopify duties/import taxes | Shopify Duties and import taxes, Duties and taxes for markets | HS code, country of origin, destination, declared value, duty/tax checkout collection |
| Carrier/customs documents | DHL/FedEx/UPS/postal official international shipping pages | Commercial Invoice, phone, accurate weight, item description, prohibited/dangerous goods |

## Finding Official Sources When Missing

1. Search official domains first: `site:gov`, `site:europa.eu`, platform Seller Center/University domains, official customs/tax/regulator domains.
2. Combine target country/platform + category + risk word: `HS code`, `customs tariff`, `VAT`, `IOSS`, `restricted product`, `prohibited product`, `dangerous goods`, `commercial invoice`, `trademark`, `medical device`, `cosmetics`, `children`, `battery`.
3. Record URL, page title, country/site, publication or update date if visible, extracted fields, and unresolved gaps.
4. If only third-party content is found, label it `non-official candidate` and ask the seller to verify with official source, Seller Center, customs broker, tax advisor, attorney, testing lab, or carrier.

For mainland China as the import destination, read `china-import-playbook.md`; do not substitute US/EU customs, certification, tax, or labeling rules.

## Accio / WorkBuddy Reuse Boundary

- Reuse Accio for field logic: origin/destination/productName for tariff, HS/COO/value for customs, Nexus/Marketplace Facilitator/OSS/IOSS for tax, IPI/capacity/stranded inventory for FBA.
- Reuse WorkBuddy for full-chain risk awareness.
- Do not use either as policy authority.
