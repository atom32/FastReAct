# FastReAct 演示程序

本目录包含 FastReAct 的各种演示程序。

## 演示列表

### 1. simple_chat.py
简单的交互式聊天演示，展示 FastReAct 的基本功能。

### 2. demo.py (根目录)
完整的演示程序，包含 5 种演示模式：
- 计算器演示
- 日期时间演示
- HTTP 请求演示
- 多工具协同演示
- 交互式对话

### 3. demo_auto.py (根目录)
自动演示程序，自动运行 4 个演示示例。

## 运行方式

```bash
# 简单聊天
python demos/simple_chat.py

# 完整演示（交互式）
python demo.py

# 自动演示
python demo_auto.py
```

## 注意事项

- 所有演示都需要先配置 `config.json` 中的 API Key
- 主要演示程序位于根目录，方便运行
- 更多示例请查看 `examples/` 目录
