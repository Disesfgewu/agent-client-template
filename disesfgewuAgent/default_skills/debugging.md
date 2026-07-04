---
name: debugging
description: Debugging techniques, error tracking, and troubleshooting common issues. Use when investigating bugs, analyzing errors, or fixing unexpected behavior.
version: 1.0.0
author: Agent Team
tags:
  - development
  - debugging
  - troubleshooting
  - error-handling
---

# Debugging Techniques

## Overview
Effective debugging is essential for maintaining and improving code quality. This skill covers systematic approaches to finding and fixing bugs.

## When to Use
- Investigating unexpected behavior or errors
- Analyzing stack traces and error messages
- Troubleshooting performance issues
- Debugging concurrency problems
- Fixing integration issues

## Debugging Process

### 1. Reproduce the Issue
- Get exact steps to reproduce
- Identify the environment (OS, versions, config)
- Create a minimal reproduction case
- Document expected vs actual behavior

### 2. Gather Information
- Read error messages carefully
- Check logs at appropriate levels
- Review recent changes (git log)
- Check related issues/tickets

### 3. Isolate the Problem
- Binary search through code/commits
- Add logging at key points
- Use debugger breakpoints
- Comment out code sections

## Common Debugging Tools

### Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Variable state: %s", variable)
logger.error("Operation failed", exc_info=True)
```

### Debuggers
- **pdb/ipdb**: Python interactive debugger
- **IDE debuggers**: VS Code, PyCharm
- **Remote debugging**: For production issues

### Profiling
- cProfile for performance issues
- Memory profilers for leaks
- Line profilers for hotspots

## Common Bug Categories

### Logic Errors
- Off-by-one errors
- Incorrect conditionals
- Wrong operator (== vs =)
- State management issues

### Concurrency Issues
- Race conditions
- Deadlocks
- Resource leaks
- Thread safety violations

### Integration Issues
- API contract mismatches
- Version incompatibilities
- Configuration errors
- Network timeouts

## Process

### Step 1: Understand the Problem
- Gather all available information
- Reproduce the issue consistently
- Identify when it started occurring

### Step 2: Form Hypotheses
- List possible causes
- Prioritize by likelihood
- Plan how to test each hypothesis

### Step 3: Test and Fix
- Test hypotheses systematically
- Implement minimal fixes
- Verify the fix doesn't break other things

## Output Format
When debugging, provide:
1. Root cause analysis
2. Steps to reproduce
3. Proposed fix
4. Prevention strategies

## Prevention Strategies
- Write tests for bug fixes
- Add assertions for assumptions
- Use type hints
- Implement defensive programming
- Code review before merge

## Notes
- Don't guess randomly - be systematic
- Sometimes the bug is in your assumptions
- Check the simplest explanations first
- Document the fix for future reference
