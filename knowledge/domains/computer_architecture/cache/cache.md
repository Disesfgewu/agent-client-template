---
name: cache
domain: computer_architecture
category: cache
requires:
  - locality
tags: [cache, memory_hierarchy, direct_mapped, set_associative]
difficulty: intermediate
description: "Cache Organization, Direct-Mapped, Set-Associative, Cache Hits, Misses, and AMAT calculation."
---

# Cache Memory & Hierarchy

## Organization
- **Direct-Mapped**: Each block maps to exactly one cache index (`Index = BlockAddress % NumBlocks`).
- **N-Way Set-Associative**: Block maps to any location in a set of N blocks.
- **Fully Associative**: Block can be placed anywhere in cache.

## Performance Equation
$\text{AMAT} = \text{Hit Time} + (\text{Miss Rate} \times \text{Miss Penalty})$
