# GitHub MCP Test Commands

## 成功！GitHub MCP 已连接

```
[INFO] Loaded 26 tools from 'github'
```

## 可用的 GitHub 工具

FastReAct 现在可以使用以下 GitHub MCP 工具：

### Issue 管理
- `create_issue` - 创建新 issue
- `update_issue` - 更新现有 issue
- `search_issues_and_prs` - 搜索 issues 和 PRs
- `add_comment` - 添加评论

### Pull Request
- `create_pull_request` - 创建 PR
- `update_pull_request` - 更新 PR
- `review_pull_request` - 审查 PR
- `merge_pull_request` - 合并 PR

### 代码操作
- `create_or_update_file` - 创建或更新文件
- `get_file_contents` - 获取文件内容
- `search_code` - 搜索代码

### 仓库管理
- `search_repositories` - 搜索仓库
- `create_repository` - 创建仓库
- `fork_repository` - Fork 仓库

## 测试命令

### 方法 1：明确指定使用 GitHub MCP

```
Use the github create_issue tool to create an issue in atom32/FastReAct repository with title "Test GitHub MCP Integration" and body "Testing TODO #16: FastReAct GitHub integration"
```

### 方法 2：更简洁的指令

```
Create a new GitHub issue in repository atom32/FastReAct
Title: "Test GitHub MCP Integration"
Body: "Testing TODO #16: FastReAct GitHub integration via MCP"
```

### 方法 3：单行命令

```
github create_issue atom32/FastReAct "Test GitHub MCP Integration" "Testing TODO #16"
```

## 当前问题

Agent 试图使用 `http` 工具而不是 `github` MCP 工具。解决方法是明确指定使用 GitHub MCP 工具。

## 验证成功的标志

看到以下输出表示成功：

```
[SimpleMCP-Stdio] Calling github.create_issue
[Result] Issue created: https://github.com/atom32/FastReAct/issues/1
```
