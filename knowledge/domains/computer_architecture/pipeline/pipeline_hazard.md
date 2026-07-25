---
name: pipeline_hazard
domain: computer_architecture
category: pipeline
requires:
  - datapath
tags: [pipeline, hazard, data_hazard, control_hazard]
difficulty: intermediate
description: "Pipeline hazards: Structural, Data (RAW, WAR, WAW), and Control Hazards."
---

# Pipeline Hazards

## Purpose
A hazard occurs when the next instruction cannot execute in the following clock cycle.

## Hazard Types
1. **Structural Hazard**: Hardware resource conflict.
2. **Data Hazard**: Instruction depends on the result of a previous instruction still in the pipeline.
   - **RAW (Read-After-Write)**: True dependency.
   - **WAR (Write-After-Read)**: Anti-dependency.
   - **WAW (Write-After-Write)**: Output dependency.
3. **Control Hazard**: Branch or jump decision depends on previous instruction.
