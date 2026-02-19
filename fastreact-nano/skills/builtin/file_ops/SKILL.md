---
name: file_ops
description: Advanced file operations and navigation
version: 1.0.0
tags: [files, filesystem, operations]
dependencies: []
---

# File Operations Skill

Advanced file operations and navigation capabilities for efficient codebase management.

## When to Use

Use this skill when you need to:
- Navigate complex directory structures
- Perform batch file operations
- Search and replace across multiple files
- Analyze file relationships and dependencies
- Manage project file organization

## Capabilities

### Directory Navigation
- Understand project structure and hierarchies
- Navigate related files efficiently
- Track file locations during operations

### Batch Operations
- Apply changes across multiple files
- Maintain consistency during bulk edits
- Verify batch operation results

### File Analysis
- Understand file relationships
- Identify dependencies and imports
- Map code organization patterns

## How it Works

This skill uses the file operation tools (read_file, write_file, edit_file, exec) to:
1. Scan directory structures
2. Read and analyze multiple files
3. Apply coordinated changes
4. Verify results

## Instructions

When working with files:
1. Always start by understanding the structure
2. Use read_file with line ranges for large files
3. Use edit_file for simple replacements
4. Use exec with sed/awk for complex batch operations
5. Verify changes after batch operations

## Examples

### Search across files
```bash
grep -r "pattern" src/
```

### Batch rename
```bash
find . -name "*.txt" -exec mv {} {}.bak \;
```

### Find large files
```bash
find . -type f -size +1M
```
