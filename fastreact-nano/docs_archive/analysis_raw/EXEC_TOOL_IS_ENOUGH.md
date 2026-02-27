# FastReAct Nano - exec 工具已足够强大

**Date**: 2025-02-27
**核心洞察**: exec 工具可以替代大部分专用工具

---

## 验证：exec 工具能做什么？

### HTTP 请求

**不需要**：http_tool.py

**只需要**：
```bash
# GET 请求
curl -s https://api.example.com

# POST 请求
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' \
  https://api.example.com

# 带认证
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com
```

**在 Skills 中提供示例**：
```yaml
---
name: http_fetch
description: Fetch HTTP content using curl
---

# HTTP Fetch

Use `exec` tool with curl:

\`\`\`bash
# GET request
curl -s https://api.example.com

# POST request
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' \
  https://api.example.com
\`\`\`
```

---

### Web 搜索

**不需要**：search_tool.py

**只需要**：
```bash
# 使用 duckduckgo (HTML 解析)
curl -s "https://duckduckgo.com/?q=fastreact+nano" | \
  grep -oP '<a[^>]+class="result__a"[^>]*>.*?</a>' | \
  head -5

# 或使用 ddgr 命令行工具
ddgr fastreact nano --json

# 或使用 brave-search CLI
brave-search "fastreact nano" --count 5
```

**在 Skills 中提供示例**：
```yaml
---
name: web_search
description: Search the web using duckduckgo
requirements:
  bins: ["curl", "grep"]
---

# Web Search

Use `exec` tool with curl and grep:

\`\`\`bash
curl -s "https://duckduckgo.com/?q={query}" | \
  grep -oP '<a[^>]+class="result__a"[^>]*>.*?</a>'
\`\`\"
```

---

### JSON 处理

**不需要**：json_tool.py

**只需要**：
```bash
# 解析并美化 JSON
echo '{"name":"test"}' | jq .

# 提取字段
curl -s https://api.example.com | jq '.data[0].name'

# 过滤数据
curl -s https://api.example.com | jq '.data[] | select(.age > 18)'

# 转换格式
curl -s https://api.example.com | jq -r '.data[] | @csv'
```

**在 Skills 中提供示例**：
```yaml
---
name: json_process
description: Process JSON using jq
requirements:
  bins: ["jq"]
---

# JSON Processing

Use `exec` tool with jq:

\`\`\`bash
# Parse JSON
echo '{\"name\":\"test\"}' | jq .

# Extract field
curl -s https://api.example.com | jq '.data[0].name'
\`\`\"
```

---

### 定时任务

**不需要**：schedule_tool.py

**只需要**：
```bash
# 列出定时任务
crontab -l

# 添加定时任务
(crontab -l 2>/dev/null; echo "* * * * * /path/to/command") | crontab -

# 删除定时任务
crontab -l | grep -v "/path/to/command" | crontab -

# 编辑 crontab
crontab -e
```

**在 Skills 中提供示例**：
```yaml
---
name: cron_manage
description: Manage cron jobs
requirements:
  bins: ["crontab"]
---

# Cron Jobs

Use `exec` tool with crontab:

\`\`\`bash
# List cron jobs
crontab -l

# Add cron job
crontab -l | { cat; echo "* * * * * /path/to/command"; } | crontab -
\`\`\"
```

---

### 图像处理

**不需要**：image_tool.py

**只需要**：
```bash
# 调整大小
convert input.jpg -resize 800x600 output.jpg

# 转换格式
convert input.png output.jpg

# 裁剪
convert input.jpg -crop 800x600+100+100 output.jpg

# 获取信息
identify input.jpg

# 批量处理
mogrify -resize 800x600 *.jpg
```

**在 Skills 中提供示例**：
```yaml
---
name: image_process
description: Process images using ImageMagick
requirements:
  bins: ["convert", "identify"]
---

# Image Processing

Use `exec` tool with ImageMagick:

\`\`\`bash
# Resize image
convert input.jpg -resize 800x600 output.jpg

# Get image info
identify input.jpg
\`\`\"
```

---

### 文件搜索

**不需要**：search_tool.py

**只需要**：
```bash
# 按名称搜索
find . -name "*.py"

# 按内容搜索
grep -r "TODO" ./

# 组合搜索
find . -name "*.py" | xargs grep "TODO"

# 高级搜索
find . -type f -mtime -7 -size +1M
```

---

### 数据库操作

**不需要**：database_tool.py

**只需要**：
```bash
# SQLite 查询
sqlite3 database.db "SELECT * FROM users WHERE age > 18"

# 导出数据
sqlite3 database.db ".dump" > backup.sql

# 导入数据
sqlite3 database.db < backup.sql

# CSV 导入
sqlite3 database.db ".import --csv data.csv users"
```

---

### Git 操作

**不需要**：git_tool.py

**只需要**：
```bash
# 查看状态
git status

# 提交更改
git add . && git commit -m "message"

# 查看日志
git log --oneline -10

# 创建分支
git checkout -b feature/new-feature
```

---

## 结论：exec 工具 + 足够的 Skills = 完整功能

### FastReAct Nano 应该做的

**✅ 保持**：
- 4 个核心工具（exec, read, write, edit）
- 简洁的代码库
- Nano 的哲学

**✅ 改进**：
- Skills 文档中提供更多 bash 命令示例
- 明确常用命令的 `requirements.bins`
- 提供"最佳实践"文档

**❌ 不要做**：
- 添加更多内建工具
- 增加不必要的依赖
- 破坏 Nano 特性

---

## Skills 应该提供什么？

### 好的 Skill 示例

```yaml
---
name: http_operations
description: Common HTTP operations using curl
tags: [http, web, api]
requirements:
  bins: ["curl", "jq"]  # 声明需要的命令
---

# HTTP Operations

Use `exec` tool with curl for HTTP requests.

## GET Request

\`\`\`bash
curl -s https://api.example.com
\`\`\`

## POST Request

\`\`\`bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"key":"value"}' \
  https://api.example.com
\`\`\`

## With Authentication

\`\`\`bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com
\`\`\`

## Parse JSON Response

\`\`\`bash
curl -s https://api.example.com | jq .
\`\`\"
```

---

## 推荐的 Skills 库

### 应该提供的 Skills

1. **http_operations** - HTTP 请求（curl）
2. **json_processing** - JSON 处理
3. **web_search** - Web 搜索（curl + grep）
4. **file_operations** - 文件操作（find, xargs）
5. **image_processing** - 图像处理
6. **database_operations** - 数据库操作（sqlite3）
7. **git_operations** - Git 操作
8. **cron_jobs** - 定时任务（crontab）

**共同特点**：
- ✅ 只使用 bash 命令
- ✅ 明确 `requirements.bins`
- ✅ 提供清晰的示例
- ✅ 零代码扩展

---

## 依赖检查

### FastReAct 应该做什么？

```python
class SkillLoader:
    def _check_requirements(self, skill: Skill) -> bool:
        """检查技能的依赖是否满足"""
        metadata = skill.metadata

        # 检查 bins 依赖
        if "requires" in metadata:
            if "bins" in metadata["requires"]:
                for bin_name in metadata["requires"]["bins"]:
                    if not shutil.which(bin_name):
                        print(f"[WARNING] Skill '{skill.name}' requires '{bin_name}' but it's not installed")
                        return False

        return True
```

**效果**：
- ✅ Agent 只加载满足依赖的技能
- ✅ 优雅降级（工具不可用时跳过）
- ✅ 清晰的错误提示

---

## 最终方案

### FastReAct Nano 的定位

**核心**：
- ✅ 4 个工具（exec, read, write, edit）
- ✅ 足够的 Skills（提供 bash 示例）
- ✅ 依赖检查（优雅降级）

**扩展方式**：
1. ✅ Skills（零代码）- bash 命令集成
2. ✅ MCP（可选）- 复杂功能
3. ❌ 不添加更多内建工具

**哲学**：
> "exec 万能，Skills 集成，保持 Nano"

---

## 优势对比

| 方案 | 代码量 | 依赖 | 扩展性 | Nano 特性 |
|------|--------|------|--------|-----------|
| **添加内建工具** | +3000 行 | +10 库 | ❌ 差 | ❌ 破坏 |
| **exec + Skills** | +500 行 | 0 库 | ✅ 好 | ✅ 保持 |

---

## 实施建议

### 立即行动（1 周）

1. **完善 Skills 文档**
   - ✅ 添加 8 个常用 Skills
   - ✅ 每个都有清晰的 bash 示例
   - ✅ 明确 `requirements.bins`

2. **改进依赖检查**
   - ✅ 检查 `bins` 是否存在
   - ✅ 优雅降级
   - ✅ 清晰的错误提示

3. **提供最佳实践**
   - ✅ "如何使用 exec 工具"文档
   - ✅ "常用 bash 命令"参考
   - ✅ Skills 编写指南

---

## 结论

**用户的观察完全正确**：
- ✅ exec 工具已经足够强大
- ✅ 大部分专用工具都可以被 bash 替代
- ✅ 通过 Skills 提供示例即可

**FastReAct Nano 应该**：
- ✅ 保持 4 个核心工具
- ✅ 通过 exec + bash 实现所有功能
- ✅ 在 Skills 中提供清晰的示例
- ✅ 不破坏 Nano 特性

**这才是 Nano 的正确打开方式！**

---

**作者**: FastReAct Team
**核心思想**: "exec 万能，Skills 集成"
**状态**: 最佳方案
