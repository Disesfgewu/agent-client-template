---
name: datapath
domain: computer_architecture
category: pipeline
requires: []
tags: [hardware, datapath, alu, registers]
difficulty: beginner
description: "CPU Datapath basics: PC, Instruction Memory, Register File, ALU, Data Memory."
---

# CPU Datapath Fundamentals

## Purpose
The Datapath is the hardware executing operations: PC update, Instruction Fetch, Register Read, ALU Computation, Memory Access, and Register Writeback.

## Core Components
- **Program Counter (PC)**: Holds the memory address of the instruction being executed.
- **Instruction Memory**: Stores instructions.
- **Register File**: 32 general-purpose registers (in RISC-V `x0`-`x31`).
- **ALU (Arithmetic Logic Unit)**: Executes arithmetic & logical operations.
- **Data Memory**: RAM storage for load/store operations (`lw`, `sw`).
