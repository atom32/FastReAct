# FastReAct 配置 Tavily API Key 快速指南

## 步骤 1: 获取 Tavily API Key

访问 https://tavily.com/ 注册并获取 API Key（免费，每月 1000 次搜索）

## 步骤 2: 填写到 config.json

打开 `config.json`，找到 `tools` 部分：

```json
{
  "tools": {
    "tavily": {
      "api_key": "tvly-你的API密钥填在这里",
      "description": "Tavily AI-optimized search API key",
      "note": "Get your API key from https://tavily.com/"
    }
  }
}
```

将你的 Tavily API Key 填入 `api_key` 字段。

## 步骤 3: 测试配置

运行演示脚本测试：

```bash
python examples/tavily_from_config.py
```

## 完成！

配置完成后，FastReAct 就可以使用 Tavily 进行 AI 优化的搜索了。

---

**注意**：如果只是测试 FastReAct 功能，不需要 Tavily。内置的计算器、时间等工具已经足够：

```bash
python demo_auto.py    # 自动演示
python demo.py         # 交互式演示
```
