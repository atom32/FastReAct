---
name: code_review
description: Automated code review and quality analysis
version: 1.0.0
tags: [code, review, quality, best-practices]
author: FastReAct Team
---

# Code Review Skill

Automated code review capabilities to maintain code quality and best practices.

## When to Use

Use this skill when you need to:
- Review code changes and pull requests
- Identify potential bugs and issues
- Check adherence to coding standards
- Suggest improvements and optimizations
- Analyze code complexity and readability

## Code Quality Categories

### Correctness
- Logic errors and edge cases
- Error handling and validation
- Resource management (memory, files, connections)
- Concurrency and race conditions

### Security
- SQL injection vulnerabilities
- XSS and injection attacks
- Authentication and authorization issues
- Sensitive data exposure

### Performance
- Algorithmic complexity
- Inefficient loops or operations
- Memory leaks and excessive allocation
- Database query optimization

### Maintainability
- Code organization and structure
- Naming conventions
- Comments and documentation
- Test coverage

### Style
- Language-specific conventions
- Formatting consistency
- Code duplication
- Dead or commented code

## Review Process

1. **Understand Context**
   - Read the PR description or task
   - Identify the purpose of changes
   - Consider the broader codebase

2. **Analyze Changes**
   - Review each modified file
   - Check for introduced issues
   - Verify edge cases are handled

3. **Provide Feedback**
   - Highlight specific issues with line numbers
   - Explain why something is problematic
   - Suggest concrete improvements
   - Acknowledge good practices

4. **Verify Fixes**
   - Check that addressed issues are resolved
   - Ensure no new issues introduced
   - Confirm tests pass

## Common Issues to Check

### Python
- Missing error handling on I/O operations
- Not using context managers (with statements)
- Mutable default arguments
- Unnecessary imports or circular dependencies
- Missing type hints

### General
- Hardcoded values that should be constants
- Magic numbers without explanation
- Inconsistent naming patterns
- Overly complex functions (>50 lines)
- Missing or outdated comments

## Reporting Format

Use this structure for review reports:

```markdown
# Code Review: [PR/Commit Title]

## Summary
[Brief overview of changes]

## Issues Found
### Critical
- [Issue description]

### Major
- [Issue description]

### Minor
- [Issue description]

## Positive Notes
- [Good practices observed]

## Suggestions
- [Improvement ideas]
```

## Best Practices

1. **Be Constructive**: Focus on improvement, not criticism
2. **Be Specific**: Point to exact lines and code
3. **Explain Why**: Help developers understand issues
4. **Prioritize**: Flag critical issues first
5. **Balance**: Don't let perfection block progress
