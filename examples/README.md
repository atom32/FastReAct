# FastReAct Examples

本目录包含示例脚本和演示代码，展示FastReAct的各种功能。

---

## 示例脚本列表

### 任务链式执行
- `demo_task_chaining.py` - 基础任务链演示
- `demo_manual_chaining.py` - 手动创建任务链

### 自动反思
- `demo_auto_reflection.py` - Sprint 5自动反思功能

### 会话管理
- `demo_session_resume.py` - 会话恢复演示

### 工作区隔离
- `demo_workspace_isolation.py` - 多租户工作区

### 编码代理
- `demo_coding_agent.py` - 代码生成和编辑

### 流式处理
- `demo_streaming.py` - 流式响应示例

### 任务调度器
- `demo_task_scheduler_simple.py` - 简单任务调度

---

## 运行示例

### 前提条件
```bash
# 1. 安装FastReAct
cd /path/to/FastReAct
pip install -e .

# 2. 配置API密钥
# 编辑 config.json 或设置环境变量
export FASTREACT_API_KEY="your-api-key"
```

### 运行特定示例
```bash
# 任务链演示
python examples/demo_task_chaining.py

# 自动反思演示
python examples/demo_auto_reflection.py

# 会话恢复演示
python examples/demo_session_resume.py
```

---

## 示例代码规范

### 命名规范
- 格式: `demo_<feature>.py`
- 清晰描述展示的功能
- 使用有意义的变量名

### 代码结构
```python
"""
Feature Name Demo

This script demonstrates the <feature> functionality of FastReAct.

Usage:
    python demo_feature.py
"""

import asyncio
from fastreact import FastReAct

async def main():
    """Main demo function"""
    print("[INFO] Starting demo...")
    
    # Create agent
    agent = FastReAct(api_key="...")
    
    # Execute example
    result = await agent.run_async("example query")
    
    print(f"[OK] Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 文档要求
1. **文件头docstring** - 描述功能和用法
2. **内联注释** - 解释关键步骤
3. **打印输出** - 使用文本标记 (`[INFO]`, `[OK]`, `[ERROR]`)
4. **错误处理** - 捕获并优雅处理异常

---

## 添加新示例

### 1. 检查是否已有类似示例
```bash
ls examples/demo_*.py
grep -r "<feature>" examples/
```

### 2. 优先更新现有示例
- 如果类似示例存在，考虑在其基础上扩展
- 避免重复演示相同功能

### 3. 创建新示例时
- 使用清晰的命名: `demo_<feature>.py`
- 添加完整的文档字符串
- 包含使用示例和预期输出
- 测试确保可运行

---

## 示例代码原则

1. **简洁性** - 展示核心功能，避免过度复杂
2. **可运行** - 示例应该可以直接运行
3. **文档化** - 充分注释，便于理解
4. **实用性** - 展示真实使用场景
5. **更新及时** - 随代码演进同步更新

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 开发规则
- [INSTALLATION.md](../INSTALLATION.md) - 安装指南
- [README.md](../README.md) - 项目概述

---

**最后更新**: 2026-02-07
