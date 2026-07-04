---
name: testing
description: Unit testing, integration testing, and test-driven development strategies. Use when writing tests, setting up test frameworks, or implementing TDD.
version: 1.0.0
author: Agent Team
tags:
  - development
  - testing
  - quality-assurance
  - tdd
---

# Testing Strategies

## Overview
Comprehensive testing ensures code quality and prevents regressions. This skill covers various testing approaches and best practices.

## When to Use
- Writing unit tests for new functionality
- Setting up integration tests
- Implementing test-driven development (TDD)
- Debugging failing tests
- Improving test coverage

## Testing Pyramid

### Unit Tests
- Test individual functions/methods in isolation
- Fast execution
- High coverage
- Use mocks for dependencies

### Integration Tests
- Test component interactions
- Verify API contracts
- Test database operations
- Slower than unit tests

### End-to-End Tests
- Test complete user workflows
- Simulate real user behavior
- Most expensive to maintain
- Use sparingly for critical paths

## Test-Driven Development (TDD)

### Red-Green-Refactor Cycle
1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code while keeping tests green

### Benefits
- Better code design
- Higher test coverage
- Documentation through tests
- Confidence in refactoring

## Process

### Step 1: Plan Your Tests
- Identify what needs to be tested
- Determine test scenarios (happy path, edge cases, errors)
- Choose appropriate test types

### Step 2: Write Tests First (TDD)
- Write clear, descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests focused and independent

### Step 3: Implement and Verify
- Write minimal code to pass tests
- Run tests frequently
- Refactor with confidence

## Best Practices

### Test Structure (AAA Pattern)
```python
def test_example():
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Naming Conventions
- `test_[function]_[scenario]_[expected_result]`
- Example: `test_calculate_total_with_discount_returns_reduced_price`

### What to Test
- Happy path scenarios
- Edge cases (empty, null, boundary values)
- Error conditions
- Different input combinations

## Mocking and Stubbing
- Use mocks for external dependencies
- Stub network calls in unit tests
- Use fixtures for test data
- Avoid over-mocking

## Output Format
When writing tests, provide:
1. Test file structure
2. Test implementations
3. Setup/teardown if needed
4. Example test runs

## Notes
- Aim for 80%+ code coverage
- Tests should be fast and reliable
- Flaky tests are worse than no tests
- Document complex test scenarios
