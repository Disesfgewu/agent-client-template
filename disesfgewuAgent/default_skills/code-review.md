---
name: code-review
description: Reviews code for bugs, security issues, and style violations. Use when reviewing pull requests, checking code quality, or conducting code audits.
version: 1.0.0
author: Agent Team
tags:
  - development
  - code-quality
  - review
  - security
---

# Code Review Best Practices

## Overview
Code review is a critical part of the software development process. This skill covers best practices for conducting effective code reviews.

## When to Use
- Reviewing pull requests or merge requests
- Checking code quality before deployment
- Conducting code audits for security vulnerabilities
- Mentoring junior developers on coding standards
- Ensuring consistency across a codebase

## Key Principles

### 1. Be Constructive
- Focus on the code, not the person
- Explain the "why" behind suggestions
- Offer alternatives, not just criticism

### 2. Check for Common Issues
- Code clarity and readability
- Proper error handling
- Security vulnerabilities
- Performance considerations
- Test coverage

### 3. Review Checklist
- [ ] Code follows project style guidelines
- [ ] Functions are appropriately sized
- [ ] Variables have meaningful names
- [ ] Comments explain complex logic
- [ ] No hardcoded secrets or credentials
- [ ] Error cases are handled
- [ ] Tests are included for new functionality

## Process

### Step 1: Understand the Context
- Read the PR description or issue
- Understand the purpose of the changes
- Identify the scope of impact

### Step 2: Review the Code
- Check for logic errors and edge cases
- Verify error handling is comprehensive
- Look for security vulnerabilities
- Assess performance implications

### Step 3: Provide Feedback
- Be specific and actionable
- Prioritize issues (critical, important, nice-to-have)
- Suggest improvements, not just problems

## Common Patterns to Look For

### Good Patterns
- Single Responsibility Principle
- DRY (Don't Repeat Yourself)
- Proper use of design patterns
- Clear separation of concerns

### Anti-Patterns
- God classes/functions
- Magic numbers
- Premature optimization
- Over-engineering

## Output Format
Provide feedback in this structure:
1. **Summary**: Overall assessment of the code
2. **Critical Issues**: Must fix before merge
3. **Improvements**: Recommended changes
4. **Positive Notes**: What was done well

## Tools and Automation
- Use linters for style checks
- Run automated tests before review
- Use static analysis tools
- Check for dependency vulnerabilities

## Notes
- Balance thoroughness with review speed
- Don't nitpick style if linters handle it
- Focus on correctness and maintainability first
