---
name: branch_prediction
domain: computer_architecture
category: pipeline
requires:
  - pipeline_hazard
tags: [branch, prediction, btb, bht]
difficulty: advanced
description: "Static and Dynamic Branch Prediction, Branch Target Buffer (BTB), and Branch History Table (BHT)."
---

# Branch Prediction Mechanisms

## Purpose
Branch prediction reduces control hazard penalties by predicting branch directions and target addresses before execution.

## Prediction Techniques
- **Static Prediction**: Always taken or predict backward taken, forward not taken.
- **Dynamic 2-Bit Predictor**: Uses 2-bit saturating counter state machine (Strongly Taken, Weakly Taken, Weakly Not Taken, Strongly Not Taken).
- **BTB (Branch Target Buffer)**: Caches target PC addresses.
