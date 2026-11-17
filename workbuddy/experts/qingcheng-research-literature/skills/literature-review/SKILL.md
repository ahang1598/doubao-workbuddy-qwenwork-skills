---
name: literature-review
display_name: 科研文献综述
display_name_en: Literature Review
description: 系统性科研文献综述专家技能，多学术数据库检索(PubMed/arXiv/Semantic Scholar)、主题综合、引文核验、多格式引用(APA/Nature/Vancouver)，生成专业markdown/PDF综述文档。覆盖系统综述全流程(计划-检索-筛选-提取-综合-验证-成稿)
description_zh: 系统性科研文献综述专家技能，多学术数据库检索(PubMed/arXiv/Semantic Scholar)、主题综合、引文核验、多格式引用(APA/Nature/Vancouver)，生成专业markdown/PDF综述文档。覆盖系统综述全流程(计划-检索-筛选-提取-综合-验证-成稿)
description_en: Systematic literature review skill with multi-database search (PubMed/arXiv/Semantic Scholar), thematic synthesis, citation verification, multi-format citations (APA/Nature/Vancouver), professional markdown/PDF output. Full systematic review workflow
category: education
version: 1.0.0
author: 青橙科教
dependency:
  python:
    - requests==2.28.0
---

# 科研文献综述

> 专门用于系统化文献综述的专业工具，核心价值在于解决学术研究中的"信息过载"问题。

## 它能做什么

- **多库并行高效检索**：同时检索多个权威学术数据库（PubMed、arXiv、Semantic Scholar），不依赖单一数据源，配置高速率专用检索 API 服务
- **自动化文献筛选**：根据研究主题自动筛选并整理相关文献，避免手动大海捞针
- **专业格式输出**：生成符合学术规范的 Markdown 或 PDF 格式报告
- **多引用格式支持**：自动生成 APA、Nature、Vancouver 等多种引用格式的参考文献

## 如何触发它

满足以下条件之一即可触发：

- **明确的文献综述需求**：如"帮我写一篇关于 XXX 的文献综述""整理一下 XXX 领域的研究进展"
- **系统性文献调研**：如"我要研究 XXX 方向，先帮我看下这个领域有哪些重要文献"
- **学术写作支撑**：撰写论文或研究计划时，需要某主题的文献基础

## 系统性综述全流程

1. **计划与范围界定**（Planning & Scoping）——明确综述问题、纳入排除标准
2. **系统性文献检索**（Systematic Search）——PubMed/arXiv/Semantic Scholar 等多库检索
3. **筛选与筛选**（Screening & Selection）——按标准筛选文献
4. **数据提取与质量评估**（Extraction & Quality Assessment）
5. **综合与分析**（Synthesis & Analysis）——主题化综合
6. **引文核验**（Citation Verification）——确保引文准确
7. **文档生成**（Document Generation）——markdown/PDF 专业输出

## 原始英文文档

以下为技能完整实现细节（英文），位于本文件下半部分，供深挖使用。

This skill integrates with multiple scientific skills for database access (gget, bioservices, datacommons-client) and provides specialized tools for citation verification, result aggregation, and document generation.

## When to Use This Skill

Use this skill when:
- Conducting a systematic literature review for research or publication
- Synthesizing current knowledge on a specific topic across multiple sources
- Performing meta-analysis or scoping reviews
- Writing the literature review section of a research paper or thesis
- Investigating the state of the art in a research domain
- Identifying research gaps and future directions
- Requiring verified citations and professional formatting

---

## Core Workflow

Literature reviews follow a structured, multi-phase workflow:

### Phase 1: Planning and Scoping

1. **Define Research Question**: Use PICO framework (Population, Intervention, Comparison, Outcome) for clinical/biomedical reviews
   - Example: "What is the efficacy of CRISPR-Cas9 (I) for treating sickle cell disease (P) compared to standard care (C)?"

2. **Establish Scope and Objectives**:
   - Define clear, specific research questions
   - Determine review type (narrative, systematic, scoping, meta-analysis)
   - Set boundaries (time period, geographic scope, study types)

3. **Develop Search Strategy**:
   - Identify 2-4 main concepts from research question
   - List synonyms, abbreviations, and related terms for each concept
   - Plan Boolean operators (AND, OR, NOT) to combine terms
   - Select minimum 3 complementary databases

4. **Set Inclusion/Exclusion Criteria**:
   - Date range (e.g., last 10 years: 2015-2024)
   - Language (typically English, or specify multilingual)
   - Publication types (peer-reviewed, preprints, reviews)
   - Study designs (RCTs, observational, in vitro, etc.)
   - Document all criteria clearly

### Phase 2: Systematic Literature Search

Select databases appropriate for the domain:

**Biomedical & Life Sciences:**
- Use `gget` skill: `gget search pubmed "search terms"` for PubMed/PMC
- Use `gget` skill: `gget search biorxiv "search terms"` for preprints
- Use `bioservices` skill for ChEMBL, KEGG, UniProt, etc.

**General Scientific Literature:**
- Search arXiv via direct API (preprints in physics, math, CS, q-bio)
- Search Semantic Scholar using the dedicated search script:
  ```bash
  python scripts/search_semantic_scholar.py "your search terms" --year 2020-2024 --output semantic_results.json
  ```
  - Covers 200M+ papers across all disciplines
  - Supports year filtering, pagination, and flexible search queries
  - Outputs results in JSON format compatible with the review workflow
- Use Google Scholar for comprehensive coverage

**Specialized Databases:**
- Use `gget alphafold` for protein structures
- Use `gget cosmic` for cancer genomics
- Use `datacommons-client` for demographic/statistical data

### Phase 3: Screening and Selection

1. **Deduplication**:
   ```bash
   python scripts/search_databases.py results.json --deduplicate --output unique_results.json
   ```
   - Removes duplicates by DOI (primary) or title (fallback)
   - Document number of duplicates removed

2. **Title Screening**:
   - Review all titles against inclusion/exclusion criteria
   - Exclude obviously irrelevant studies
   - Document number excluded at this stage

3. **Abstract Screening**:
   - Read abstracts of remaining studies
   - Apply inclusion/exclusion criteria rigorously
   - Document reasons for exclusion

4. **Full-Text Screening**:
   - Obtain full texts of remaining studies
   - Conduct detailed review against all criteria
   - Document specific reasons for exclusion
   - Record final number of included studies

### Phase 4: Data Extraction and Quality Assessment

1. **Extract Key Data** from each included study:
   - Study metadata (authors, year, journal, DOI)
   - Study design and methods
   - Sample size and population characteristics
   - Key findings and results
   - Limitations noted by authors
   - Funding sources and conflicts of interest

2. **Assess Study Quality**:
   - **For RCTs**: Use Cochrane Risk of Bias tool
   - **For observational studies**: Use Newcastle-Ottawa Scale
   - **For systematic reviews**: Use AMSTAR 2
   - Rate each study: High, Moderate, Low, or Very Low quality
   - Consider excluding very low-quality studies

3. **Organize by Themes**:
   - Identify 3-5 major themes across studies
   - Group studies by theme (studies may appear in multiple themes)
   - Note patterns, consensus, and controversies

### Phase 5: Synthesis and Analysis

See [references/database_strategies.md](references/database_strategies.md) for detailed guidance on search execution.

### Phase 6: Citation Verification

Verify all citations using the citation verification script:
```bash
python scripts/verify_citations.py literature_review.md
```

This script will:
- Extract all DOIs from the document
- Verify each DOI against the CrossRef API
- Check URL accessibility
- Generate a verification report

### Phase 7: Document Generation

1. **Write the Review**:
   - Use the template from [assets/review_template.md](assets/review_template.md)
   - Follow PRISMA guidelines for systematic reviews
   - Include all necessary sections (Introduction, Methods, Results, Discussion)

2. **Format Citations**:
   - See [references/citation_styles.md](references/citation_styles.md) for style guidelines
   - Choose appropriate citation style (APA, Nature, Vancouver, etc.)
   - Ensure consistency throughout the document

3. **Generate PDF**:
   ```bash
   python scripts/generate_pdf.py literature_review.md --citation-style apa
   ```
   - Requires pandoc and xelatex to be installed
   - Supports multiple citation styles
   - Generates professionally formatted PDFs

---

## Resources

### Scripts

- **[scripts/search_semantic_scholar.py](scripts/search_semantic_scholar.py)**:
  - Search Semantic Scholar database (200M+ papers) with API key
  - Rate limit: 1 request/second (vs 0.33/second without key)
  - Supports year filtering, pagination, and flexible queries
  - Outputs results in JSON format compatible with search_databases.py

- **[scripts/search_databases.py](scripts/search_databases.py)**:
  - Format search results in JSON, Markdown, or BibTeX
  - Deduplicate results by DOI or title
  - Filter results by year
  - Rank results by citations, year, or relevance

- **[scripts/verify_citations.py](scripts/verify_citations.py)**:
  - Verify DOIs against CrossRef API
  - Check URL accessibility
  - Format citations in APA or Nature style
  - Generate verification reports

- **[scripts/generate_pdf.py](scripts/generate_pdf.py)**:
  - Convert markdown to PDF using pandoc
  - Support for multiple citation styles
  - Include table of contents and section numbering

### References

- **[references/database_strategies.md](references/database_strategies.md)**: Comprehensive guide to searching multiple academic databases, including search syntax, database-specific tips, and best practices.

- **[references/citation_styles.md](references/citation_styles.md)**: Detailed guidelines for formatting citations in various academic styles (APA, Nature, Chicago, Vancouver, IEEE).

### Assets

- **[assets/review_template.md](assets/review_template.md)**: Complete template for writing literature reviews, following PRISMA guidelines for systematic reviews.

---

## Best Practices

1. **Document Everything**: Record all search strings, dates, databases, and inclusion/exclusion criteria for reproducibility.

2. **Use Multiple Databases**: Search at least 3 complementary databases to ensure comprehensive coverage.

3. **Verify Citations**: Always verify DOIs and URLs before final submission to ensure accuracy.

4. **Quality Assessment**: Systematically assess study quality using appropriate tools for the study type.

5. **Thematic Synthesis**: Organize findings by themes rather than study-by-study to identify patterns and gaps.

6. **Professional Formatting**: Use the provided tools and templates to generate professionally formatted documents.

---

## Notes

- This skill focuses on the systematic review process and document generation.
- For actual database access, integrate with specialized skills like `gget`, `bioservices`, or `datacommons-client`.
- The scripts provided handle formatting, verification, and PDF generation but do not include database search functionality (use appropriate database-specific tools).
