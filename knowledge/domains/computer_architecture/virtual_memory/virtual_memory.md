---
name: virtual_memory
domain: computer_architecture
category: virtual_memory
requires: []
tags: [virtual_memory, page_table, page_fault, paging]
difficulty: intermediate
description: "Virtual Memory concepts, Page Tables, Virtual to Physical Address Translation."
---

# Virtual Memory

## Purpose
Provides illusion of large main memory, isolates process address spaces, and implements memory protection.

## Translation
Virtual Address (VPN + Page Offset) -> Physical Address (PPN + Page Offset).
Indexed via Page Table entries containing Physical Page Numbers and valid/dirty/protection bits.
