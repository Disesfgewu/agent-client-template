---
name: skill-creator
description: Create or update repository skills with discovery-oriented metadata, concise Markdown instructions, optional resources, registry entries, tests, and validation. Use when adding a new skill, rewriting an existing skill, designing skill structure, or producing a complete skill prompt.
version: 1.0.0
author: Agent Team
tags:
  - skills
  - creation
  - prompt-engineering
  - maintenance
---

# Skill Creator

Create skills that are easy to retrieve, cheap to inject, grounded in evidence, and safe to run in this repository's skill loader.

## Purpose
Use this skill to produce or revise `skills/*.md` files for this repo. The output should be a complete Markdown skill with YAML frontmatter, a clear operational body, registry guidance, and validation steps.

## Core Rules
- Optimize the YAML `description`; this repo embeds descriptions for retrieval, so body-only trigger text does not help selection.
- Keep the body concise and operational. Assume the agent already knows general programming and writing basics.
- Give the skill one distinct user intent. If it overlaps another skill, define the boundary or merge the content.
- Use progressive disclosure: keep core workflow in the skill body; move large schemas, long examples, templates, or scripts into resources only when needed.
- Separate read-only analysis from write, execution, network, database, credential, deployment, and financial actions.
- Add validation instructions that match the skill's domain: tests, citations, diffs, schema checks, screenshots, calculations, or safety review.

## Frontmatter Contract
For this repository, write frontmatter in this shape:

```yaml
---
name: short-hyphen-name
description: Specific trigger-rich description. Include what the skill does and when to use it.
version: 1.0.0
author: Agent Team
tags:
  - primary-domain
  - secondary-domain
---
```

Requirements:
- `name` must be lowercase hyphen-case.
- `description` must be specific, at least 20 characters, and include user trigger terms.
- `tags` should improve maintenance and browsing, but do not rely on tags for retrieval.

## Creation Workflow
1. Identify the target user intent, non-goals, expected inputs, and expected output.
2. Check existing skills for overlap before creating a new one.
3. Choose the lowest-complexity structure: instructions-only first, then references/scripts/assets only when repeated deterministic behavior justifies them.
4. Draft frontmatter with retrieval terms a user would actually type.
5. Draft the body with: purpose, trigger boundary, workflow, tool/resource rules, safety rules, validation, and output format.
6. If the skill can cause L1-L3 risk, route it through `agent-skill-security-audit` and add explicit controls.
7. If the skill should improve retrieval or reduce prompt cost, route it through `skills-optimize` and score CP-grounding.
8. Register the file in `config/skills.example.json` and, if applicable, `config/skills.json` without copying stale embeddings.
9. Update offline tests when the skill is part of the default bundled set.
10. Run offline validation for frontmatter and registry coverage.

## Body Template
Use this minimal template unless the domain needs something else:

```markdown
# Skill Title

One-sentence operational purpose.

## Purpose
What this skill helps the agent do and why it should be reusable.

## When to Use
- Positive trigger.
- Positive trigger.

## Do Not Use When
- Boundary or overlap case.

## Workflow
1. Step one.
2. Step two.
3. Validate.

## Safety
- Read-only default.
- Approval boundary for L2/L3 actions.

## Output
Required result shape.
```

## Quality Checklist
- Description alone is enough for retrieval.
- Scope is narrower than `general-tasks` and distinct from neighboring skills.
- Body contains concrete actions, not generic advice.
- Tool and file operations are bounded.
- Sensitive data and external export rules are explicit.
- Validation command or validation method is named.
- The skill passes `tests.test_skillLoader.TestDefaultSkills`.

## Output Format
When asked to create or revise a skill, return:

1. Skill filename.
2. Complete Markdown content or applied file changes.
3. Registry entry.
4. Risk level and required safety controls.
5. Validation performed or recommended.