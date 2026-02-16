# FastReAct Test Suite

本目录包含所有测试代码，按功能和类型组织。

---

## 目录结构

```
tests/
├── conftest.py                    # Pytest配置和fixtures
├── README.md                      # 本文件
│
├── context/                       # Context管理测试
│   └── ...
│
├── core/                          # 核心功能测试
│   ├── test_engine.py
│   ├── test_react_agent.py
│   └── ...
│
├── mcp_verification/              # MCP集成验证
│   └── ...
│
└── memory/                        # Memory管理测试
    └── ...
```

---

## 测试文件命名规范

### Unit Tests (单元测试)
- 格式: `test_<module>.py`
- 示例: `test_engine.py`, `test_context_monitor.py`
- 位置: `tests/core/` 或按功能分类的子目录

### Integration Tests (集成测试)
- 格式: `test_<feature>_integration.py`
- 示例: `test_mcp_integration.py`, `test_cli_integration.py`
- 位置: `tests/` 根目录或特定子目录

### Feature-Specific Tests (功能特定测试)
- 格式: `test_<feature>_<aspect>.py`
- 示例: `test_sandbox_presets.py`, `test_policy_integration.py`
- 位置: 对应功能的子目录

---

## 运行测试

### 运行所有测试
```bash
pytest tests/
```

### 运行特定测试文件
```bash
pytest tests/core/test_engine.py
```

### 运行特定测试函数
```bash
pytest tests/core/test_engine.py::test_build_messages
```

### 运行带覆盖率的测试
```bash
pytest tests/ --cov=src/fastreact --cov-report=html
```

### 运行并显示详细输出
```bash
pytest tests/ -v -s
```

---

## 添加新测试的规则

### 1. 检查是否已存在相似测试
```bash
# 搜索相关测试
grep -r "test.*<feature>" tests/
```

### 2. 优先修改现有测试
- 如果相关测试文件存在，在其中添加新测试用例
- 避免创建新的测试文件，除非真的需要

### 3. 新建测试文件时
- 使用清晰的命名: `test_<module>.py`
- 放在合适的子目录中
- 添加必要的文档字符串和注释

### 4. 测试用例命名
- 使用描述性名称: `test_<功能>_<场景>`
- 示例: `test_memory_flush_with_soft_threshold`

---

## 测试编写指南

### 基本结构
```python
import pytest
from fastreact.core.engine import ReActEngine

class TestReActEngine:
    """ReActEngine单元测试"""
    
    def test_build_messages(self):
        """测试消息构建"""
        engine = ReActEngine(...)
        messages = engine._build_messages("test query")
        assert len(messages) > 0
        assert messages[0]["role"] == "system"
    
    def test_context_truncation(self):
        """测试上下文截断"""
        # 测试代码
        ...
```

### 使用Fixtures
```python
@pytest.fixture
def sample_engine():
    """提供测试用的engine实例"""
    return ReActEngine(model="gpt-4")

def test_with_fixture(sample_engine):
    """使用fixture的测试"""
    result = sample_engine.run("test")
    assert result is not None
```

---

## 测试分类说明

### Unit Tests (单元测试)
- 测试单个类或函数
- 不依赖外部服务
- 运行速度快

### Integration Tests (集成测试)
- 测试多个组件协作
- 可能依赖外部服务（API,数据库）
- 使用标记区分: `@pytest.mark.integration`

### Verification Tests (验证测试)
- 验证特定功能或集成
- 通常在 `mcp_verification/` 中
- 确保第三方集成正常工作

---

## 注意事项

1. **测试独立性** - 每个测试应该独立运行，不依赖其他测试
2. **清理资源** - 测试后清理临时文件和资源
3. **Mock外部依赖** - 对于API调用等外部依赖，使用mock
4. **清晰的断言** - 使用有意义的断言消息
5. **避免硬编码路径** - 使用 `pathlib.Path` 和临时目录

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 开发规则
- [DEVELOPMENT_LOG.md](../DEVELOPMENT_LOG.md) - 开发历程

---

**最后更新**: 2026-02-07
