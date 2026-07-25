---
name: forwarding
domain: computer_architecture
category: pipeline
requires:
  - datapath
  - pipeline_hazard
tags: [hardware, hazard, forwarding, bypass]
difficulty: intermediate
citation_sources:
  - "NCKU Computer Architecture Lecture Notes"
  - "Patterson & Hennessy Chapter 4.7"
description: "Hardware forwarding (bypassing) mechanism for resolving RAW data hazards in CPU pipelines."
---

# Forwarding (Bypassing) Mechanism

## Purpose
Forwarding resolves RAW data hazards by routing computed results directly from pipeline registers (EX/MEM or MEM/WB) back to the ALU inputs, avoiding pipeline stalls.

## Hardware Logic
- **Comparators**: Check if destination register matches source registers (`EX/MEM.RegisterRd == ID/EX.RegisterRs1`).
- **Multiplexers**: Select whether ALU input comes from Register File, EX/MEM pipeline register, or MEM/WB pipeline register.

## Control Conditions
- `EX/MEM.RegWrite` AND `EX/MEM.RegisterRd != 0` AND `EX/MEM.RegisterRd == ID/EX.RegisterRs1` => Forward from EX/MEM.
- `MEM/WB.RegWrite` AND `MEM/WB.RegisterRd != 0` AND `MEM/WB.RegisterRd == ID/EX.RegisterRs1` => Forward from MEM/WB.
