---
name: web-research
description: Conduct safe web research with source quality checks, current information validation, citation discipline, and ddgs-style search workflows. Use when a task needs recent facts, external sources, or market and technical verification.
version: 1.0.0
author: Agent Team
tags:
  - research
  - web
  - ddgs
  - verification
---

# Web Research

Research the web defensively: verify recency, source quality, and claims before using them.

## When to Use
- The user asks for latest, current, news, prices, laws, APIs, packages, products, market data, or citations.
- Local knowledge may be stale or the answer depends on a specific page, paper, dataset, or release.

## Safe Search Workflow
1. Classify the request as public research, private-data research, market/financial research, or technical documentation lookup.
2. Turn the request into precise search queries with entity names, dates, version numbers, or official source terms.
3. Prefer primary sources: official docs, filings, standards, academic papers, exchanges, regulators, vendor pages, and source repositories.
4. Use broad search only to discover candidates. Verify important claims against primary or independent sources.
5. Capture source title, URL, publication date, retrieval date, and the exact fact used.
6. Compare dates carefully. Treat undated pages, SEO pages, and generated summaries as weak evidence.
7. For ddgs-style tooling, keep searches narrow, avoid credentialed pages, and do not execute downloaded content.
8. Do not send private workspace content, secrets, or proprietary documents to external search or embedding services without explicit user approval.

## Using `ddgs` (search)
When code execution is enabled, run searches with the `ddgs` library (a safe,
keyless DuckDuckGo search wrapper) from an `execute` python step, then fetch only
the specific pages you need:
```python
from ddgs import DDGS
for r in DDGS().text("<precise query with entities / dates / versions>", max_results=5):
    print(r["title"], "|", r["href"])
```
Keep queries narrow, prefer official/primary sources, never send secrets or
private files to the search service, and do not execute anything you download.

## Source Quality
- Strong: official documentation, regulator/exchange data, repo releases, standards bodies, peer-reviewed papers.
- Medium: reputable journalism, vendor blogs for their own products, maintained technical blogs with code.
- Weak: scraped pages, forum claims without reproduction, content farms, outdated tutorials, unsourced summaries.

## Grounding Rules
- Tie every important claim to a source, a local file, or a clearly stated inference.
- Prefer quote-free paraphrase; quote only short fragments when wording matters.
- For finance, law, health, security, and package/version answers, verify freshness with current primary sources.
- State when search was not performed or when external retrieval was blocked by privacy policy.

## Output
Summarize findings with citations, confidence level, unresolved uncertainty, and any date-sensitive assumptions. For research that affects money, law, health, or security, explicitly state verification limits.
