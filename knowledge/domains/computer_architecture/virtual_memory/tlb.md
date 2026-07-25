---
name: tlb
domain: computer_architecture
category: virtual_memory
requires:
  - virtual_memory
  - cache
tags: [tlb, translation_lookaside_buffer, virtual_memory, cache]
difficulty: advanced
description: "Translation Lookaside Buffer (TLB) for fast virtual-to-physical address translation."
---

# Translation Lookaside Buffer (TLB)

## Purpose
A specialized hardware cache that stores recent Virtual Page Number (VPN) to Physical Page Number (PPN) translations, avoiding slow Page Table page table walks in RAM.

## Access Flow
1. CPU issues Virtual Address.
2. Lookup VPN in TLB.
   - **TLB Hit**: Retrieve PPN immediately and construct Physical Address.
   - **TLB Miss**: Walk Page Table in memory, update TLB entry, and proceed.
