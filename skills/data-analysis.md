---
name: data-analysis
description: Analyze tabular, time-series, experimental, and quantitative data with statistical rigor, reproducible notebooks or scripts, visualization, and bias checks. Use for CSV, Excel, database extracts, metrics, and financial research.
version: 1.0.0
author: Agent Team
tags:
  - data
  - analysis
  - statistics
  - quant
---

# Data Analysis

Analyze data with reproducibility, sanity checks, and explicit assumptions.

## When to Use
- Exploring CSV, Excel, SQL extracts, logs, metrics, experiment results, or financial time series.
- Building factors, backtests, reports, charts, or statistical summaries.

## Core Workflow
1. Identify the question, population, time range, unit of observation, and decision the analysis supports.
2. Load data with typed schemas. Record source, extraction time, filters, and row counts.
3. Validate quality: missingness, duplicates, outliers, joins, survivorship bias, look-ahead bias, and timezone issues.
4. Compute simple baselines before complex models.
5. Visualize distributions, time variation, and residuals. Avoid only reporting aggregate averages.
6. Separate exploration from confirmatory tests. Keep transformations reproducible.

## Quant Finance Notes
- Align signals and returns by tradable timestamp to avoid look-ahead bias.
- Include fees, slippage, liquidity, corporate actions, and realistic execution assumptions.
- Report turnover, drawdown, exposure, capacity, and regime sensitivity, not only Sharpe.

## Output
Return methods, assumptions, validation checks, key tables or charts, reproducible code or query snippets, and conclusions with confidence and caveats.
