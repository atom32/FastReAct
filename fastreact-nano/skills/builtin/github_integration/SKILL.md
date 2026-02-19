---
name: github_integration
description: GitHub integration using MCP tools for repository and PR management
version: 1.0.0
tags: [github, repository, pull-requests, collaboration]
mcp_servers: [github_mcp]
recommended_tools: [github_mcp_create_or_update_file, github_mcp_push_files]
---

# GitHub Integration Skill

Advanced GitHub operations using MCP tools for repository and pull request management.

## When to Use

Use this skill when you need to:
- Create or update files in a GitHub repository
- Create pull requests
- Manage GitHub issues
- Interact with GitHub repositories
- Collaborate on GitHub projects

## Available MCP Tools

The following MCP tools are available for this skill:

- `github_mcp_create_or_update_file`: Create or update files in a GitHub repository
- `github_mcp_push_files`: Push multiple files to a repository
- Additional GitHub tools from the github_mcp server

## Tool Usage

### Creating/Updating Files

When you need to create or update files in a GitHub repository, use the `github_mcp_create_or_update_file` tool.

Example workflow:
1. Analyze the required file changes
2. Use `github_mcp_create_or_update_file` with:
   - Repository owner and name
   - Branch name
   - File path
   - File content
   - Commit message

### Creating Pull Requests

To create a pull request:
1. Make file changes using MCP tools
2. Create a PR using the GitHub MCP tools
3. Provide clear PR title and description

### Best Practices

- Always provide clear commit messages
- Use descriptive branch names (e.g., `feature/name`, `bugfix/name`)
- Include PR descriptions that explain:
  - What changes were made
  - Why the changes are needed
  - How to test the changes
- Reference related issues in commits and PRs

## Integration with Git Workflow

This skill works best when combined with the `git_workflow` skill:
- Use `git_workflow` for local git operations
- Use `github_integration` for GitHub-specific operations
- Together they provide complete Git + GitHub workflow

## Example Scenarios

### Scenario 1: Fix a Bug

1. User reports a bug in the repository
2. Use `github_mcp_create_or_update_file` to fix the bug
3. Create a pull request with description
4. Link to original issue

### Scenario 2: Add New Feature

1. Understand requirements from user
2. Create new files or update existing ones
3. Use MCP tools to push changes
4. Create PR for review

### Scenario 3: Update Documentation

1. Read existing documentation
2. Make updates using MCP tools
3. Commit with clear message: "docs: update README"
4. Create PR if changes are significant

## Repository Context

When working with repositories:
- Always verify repository owner and name
- Check if you have the right permissions
- Use appropriate branches (never commit directly to main)
- Follow the project's contribution guidelines

## Error Handling

If MCP tools fail:
- Check authentication status
- Verify repository access permissions
- Ensure branch exists
- Check file path is correct
- Review commit message format
