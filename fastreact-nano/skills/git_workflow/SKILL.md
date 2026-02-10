---
name: git_workflow
description: Git workflow and version control operations
version: 1.0.0
tags: [git, version-control, workflow]
---

# Git Workflow Skill

Version control operations and Git workflow management.

## When to Use

Use this skill when you need to:
- Create and manage branches
- Commit changes with proper messages
- Handle merges and resolve conflicts
- Work with remotes and pull requests
- Understand git history and blame

## Common Operations

### Branching
```bash
# Create new branch
git checkout -b feature/name

# List branches
git branch -a

# Delete branch (local)
git branch -d feature/name

# Delete branch (remote)
git push origin --delete feature/name
```

### Committing
```bash
# Stage files
git add file.py
git add .

# Commit with message
git commit -m "feat: add new feature"

# Amend last commit
git commit --amend

# Commit message format
# type(scope): subject
# types: feat, fix, docs, style, refactor, test, chore
```

### Merging
```bash
# Merge branch into current
git merge feature/name

# Rebase current branch onto another
git rebase main

# Abort merge/rebase
git merge --abort
git rebase --abort
```

### History
```bash
# View log
git log --oneline --graph --all

# View file history
git log --follow file.py

# Blame (who changed what)
git blame file.py

# Show commit details
git show <commit-hash>
```

### Remotes
```bash
# Push branch
git push -u origin feature/name

# Pull with rebase
git pull --rebase

# Fetch all remotes
git fetch --all

# View remotes
git remote -v
```

## Workflows

### Feature Branch Workflow
1. Create branch from main
2. Make commits
3. Push to remote
4. Create pull request
5. Review and merge
6. Delete branch

### Gitflow Workflow
1. main (production) - releases only
2. develop (integration) - feature branches
3. feature/* - new features
4. release/* - release preparation
5. hotfix/* - emergency fixes

### Trunk-Based Development
1. All work happens on main
2. Use feature flags for unreleased features
3. Short-lived branches (<1 day)
4. Continuous integration

## Conflict Resolution

When conflicts occur:

1. **Identify Conflict Files**
   ```bash
   git status
   ```

2. **Edit Files**
   - Look for `<<<<<<<`, `=======`, `>>>>>>>`
   - Choose which version to keep
   - Remove conflict markers

3. **Mark Resolved**
   ```bash
   git add <resolved-file>
   ```

4. **Complete Merge**
   ```bash
   git commit
   ```

## Best Practices

- Write clear, descriptive commit messages
- Keep commits atomic (one logical change)
- Pull before pushing
- Use `.gitignore` properly
- Never commit secrets or API keys
- Review changes before committing
- Use branches for all work
- Keep history clean (avoid merge commits)
