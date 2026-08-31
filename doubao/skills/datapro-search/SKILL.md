---
name: datapro-search
description: Use when the user invokes $datapro-search, mentions DataPro Search, or asks for a focused search of academic literature, company registry records, company risk, securities and financial data, vehicle specifications, vehicle sales, news, policy interpretation, reference knowledge, event tracking, or general factual information.
---

# DataPro Search

## Overview

Use this skill for focused professional-data retrieval through the DataPro Search MCP. Its user-supplied scope covers academic literature, company registry and risk records, securities and financial metrics, vehicle specifications and sales, and general information research. Submit one clear data intent at a time and never merge unrelated domains into one search.

## Core Rules

- Use the live callable `dataPro_search` tool only when it is available in the current runtime.
- Select one intent category for each call: academic literature, company registry, company risk, securities and finance, vehicle specifications, vehicle sales, or general information.
- Do not combine registry, risk, finance, vehicle, academic, or general-information intents in one query. Split a multi-domain request into separate calls and label each result.
- Include the target subject and the specific information sought. Do not submit vague prompts when a company, security, vehicle, publication, or time range can be stated precisely.
- Follow the live callable interface when it differs from this guide. Do not invent company IDs, credit codes, security identifiers, prices, metrics, vehicle attributes, sales, publications, dates, events, or source facts.
- Treat provider output as evidence. Label model interpretation, calculations, summaries, risk assessments, and recommendations separately.
- Keep secrets, private content, and authorization material out of prompts, logs, and final answers. Never ask the user to paste credentials into chat.
- Do not use shell commands, direct HTTP calls, or hand-written JSON-RPC to recreate, probe, or simulate the MCP server.
- Require explicit confirmation before any external write, send, purchase, order, deletion, publication, merge, or permission change.

## Tools

- `dataPro_search`: Searches CNKI, Wanfang, and VIP academic literature; company registry and risk records; securities and financial metrics; vehicle specifications and sales; news; policy interpretation; reference knowledge; event tracking; and general factual topics.

## Workflow

1. Identify the single requested intent, target subject, keywords, time range, geographic scope, and requested output.
2. Classify the request as academic literature, company registry, company risk, securities and finance, vehicle specifications, vehicle sales, or general information before composing the query.
3. Normalize only unambiguous names and identifiers. Preserve the user's original wording when a normalization is uncertain, and ask for clarification when different entities could match.
4. Build one concise query containing the target and the requested data dimension. For a multi-domain request, run separate calls rather than combining domains in one query.
5. For company registry or risk retrieval, list one to five companies explicitly and preserve their input order. Use a precise risk dimension such as litigation, dishonesty enforcement, operating abnormality, liquidation, or negative public opinion.
6. For securities and finance retrieval, use a standardized security name or provider-recognized identifier. Include the requested metric and an explicit time range whenever the request is period-dependent.
7. For vehicle specifications, identify at least a brand, manufacturer, series, or model and name the desired specification. For vehicle sales, identify at least a brand, manufacturer, or series and state the aggregation level and time period.
8. For academic literature, include at least one precise condition: full topic, author, journal, or DOI. Add a time range to topic searches.
9. Inspect the outer MCP error, provider status, matched entities, result scope, and freshness before summarizing. Do not treat fuzzy, empty, partial, or capped results as complete.

## Query Guidance

- Keep each call focused on one explicit intent even when the same subject appears across multiple domains.
- Prefer a company's registered full name or unified social credit code for registry and risk searches. If no result is found, retry once with an unambiguous short name.
- Limit each company registry or risk query to one through five explicitly named companies. Do not silently omit companies when the request exceeds that limit; split the work into ordered batches.
- Preserve provider matching limits for company searches: one company may return up to five similar matches; two companies may return up to five matches each; three may return up to three each; four or five may return up to two each. Treat the provider's company-ID deduplication and global cap of ten results as coverage limits.
- Ask for a concrete company-risk dimension instead of interpreting a vague request such as whether a company is "good" or "safe."
- Use a normalized name or market-qualified identifier for stocks, funds, convertible bonds, futures, and options. Preserve exchange and market suffixes when supplied, and do not infer a security from an ambiguous short name.
- Distinguish a price or market-data request from a financial-metric request and state the requested period, such as the latest observation or a defined week.
- For vehicle specifications, include the model year when relevant and name dimensions such as price, powertrain, battery, range, driver assistance, safety, cabin, or body size.
- For vehicle sales, state a month or range and a national, provincial, or city aggregation level. If no time is supplied, use the provider's latest available statistical month and disclose that default. Do not request configuration fields in a sales query.
- For academic topic searches, state a concrete period such as the most recent year or three years. Use exact authors, journals, or DOI values when available.
- For news, policy, event tracking, and other time-sensitive general research, state the subject and an explicit date range whenever freshness matters.

## Failure Handling

- If no live `dataPro_search` callable tool is present, stop MCP execution and report that DataPro Search is unavailable in the current runtime.
- If the query mixes multiple intent categories, separate it into focused calls before execution or ask the user which category has priority when separation would change the requested outcome.
- For authorization, quota, timeout, invalid-query, permission, provider, or missing-tool errors, report the failed search without exposing secrets.
- Retry at most once only after a safe correction such as using a registered company name, adding an exact identifier, narrowing the date range, specifying a risk dimension, or splitting an oversized company list.
- For empty, fuzzy, partial, deduplicated, or capped results, report the exact query scope and limitation. Never fill missing records, prices, metrics, publications, vehicle attributes, sales, or events from memory.
- If a security, company, vehicle, author, journal, or topic remains ambiguous after one safe correction, stop and request the missing disambiguation.
- If the user specifically requests DataPro Search, do not silently substitute another provider. State the connector failure first and offer a clearly labeled fallback only if the user wants it.

## Result Contract

- Separate returned provider facts from model summaries, comparisons, calculations, risk interpretations, and recommendations.
- Preserve names, company IDs, credit codes, security identifiers, DOI values, dates, time ranges, currencies, units, geographic levels, filters, totals, and provider caveats when returned.
- State the matched entity and search scope so the user can detect a fuzzy company, security, vehicle, or publication match.
- Report batching, deduplication, per-company match limits, and the global result cap when they affect completeness.
- State the data period for financial, vehicle-sales, academic, news, policy, and event-tracking results. Do not present one page, fuzzy set, sample, or capped response as exhaustive.
