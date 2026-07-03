---
name: skills-optimize
description: Optimize an agent skill library by auditing coverage, metadata, retrieval quality, duplication, CP value, grounding, safety risk, and API-triggered maintenance workflows. Use when adding, revising, registering, testing, evaluating, or improving skills.
version: 1.1.0
author: Agent Team
tags:
  - skills
  - optimization
  - retrieval
  - grounding
  - maintenance
---

# Skills Optimize

Improve a skill library so the right skill is retrieved, concise enough to inject, grounded enough to reduce hallucination, and safe enough to operate in a real workspace.

## Research-Grounded Objective
Optimize for CP-grounding value: high task coverage and retrieval precision per token, while preserving evidence discipline and safety controls.

Use this score model during audits:

```text
CP-grounding = demand_fit + retrieval_fit + evidence_fit + maintainability_fit - token_cost - overlap_cost - risk_cost
```

- `demand_fit`: skill covers frequent or high-value user intents.
- `retrieval_fit`: description contains realistic trigger terms and the expected skill appears in top retrieval results.
- `evidence_fit`: workflow tells the agent what evidence to inspect, cite, validate, or refuse to infer.
- `maintainability_fit`: scope, owner assumptions, output contract, and failure handling are clear.
- `token_cost`: body is longer than needed for prompt injection.
- `overlap_cost`: intent duplicates another skill without a clean boundary.
- `risk_cost`: tool, file, network, credential, execution, or state-changing behavior lacks guardrails.

## When to Use
- Adding new skills, tuning descriptions, splitting overlapping skills, or improving retrieval quality.
- Designing an API or tool operation that audits, registers, tests, or ranks skills.
- Evaluating whether a skill should be instruction-only or should use scripts, references, or assets.

## Optimization Workflow
1. Inventory all skill files and registry entries.
2. Validate frontmatter: `name`, `description`, `version`, `author`, and useful `tags`.
3. Classify the skill by user intent, category, risk level, required tools, and expected evidence.
4. Check descriptions for retrieval terms users actually type, including synonyms and domain words.
5. Detect overlap. Merge duplicate skills or split broad skills into clear domains.
6. Keep bodies operational: trigger boundary, workflow, decision points, evidence requirements, validation, output format, and failure modes.
7. Move long domain material to references when the body approaches prompt-budget pressure.
8. Run offline tests for formatting and registry coverage.
9. Run retrieval smoke tests only when privacy policy allows sending descriptions and queries to the embedding provider.

## Skill Design Rules
- Put retrieval-critical words in `description`; body text is not available until after selection.
- Prefer one skill per distinct user intent. Avoid marketplace-style near-duplicates with different names.
- Make the first workflow step evidence gathering when the task depends on code, data, documents, market facts, or external sources.
- Add explicit negative conditions when a skill is commonly confused with another skill.
- Separate read-only analysis from write, execution, network, deployment, database, financial, or credential actions.
- Include a validation step even for non-code skills: citation check, file diff, schema check, viewport check, calculation check, or assumption check.

## API Operation Contract
Expose optimization as explicit operations rather than hidden edits:

```json
{
  "operation": "audit|register|lint|retrieve_test|suggest_rewrite|apply_rewrite|score_cp_grounding",
  "skill": "optional skill name",
  "query": "optional retrieval test query",
  "expectedSkill": "optional expected top result",
  "riskLevel": "L0|L1|L2|L3",
  "allowExternalEmbedding": false,
  "dryRun": true
}
```

Expected results should include changed files, registry actions, lint findings, retrieval scores, CP-grounding score, risk flags, and recommended next action.

## Risk Levels
- `L0`: read-only public information or safe content generation.
- `L1`: reads private, local, user-specific, or potentially sensitive data.
- `L2`: writes files, sends messages, changes repository state, or performs other reversible state changes.
- `L3`: destructive, privileged, credential, deployment, database mutation, financial, arbitrary command execution, or external data export actions.

## Quality Gates
- Every skill file is registered or intentionally excluded.
- Every registered path exists.
- Descriptions are specific, more than 20 characters, and contain trigger terms.
- Skill body is concise enough for prompt injection and concrete enough to guide execution.
- Skill boundaries reduce redundancy rather than multiplying aliases.
- Evidence and validation steps are explicit for grounded answers.
- Retrieval tests show the intended skill in the top results for representative prompts, or the description is revised.
- L2/L3 actions require clear approval, dry-run, or rollback guidance.

## Output
Return an audit table with `skill`, `intent`, `risk`, `retrieval_terms`, `overlap`, `CP-grounding score`, `fix`, and `verification command`.