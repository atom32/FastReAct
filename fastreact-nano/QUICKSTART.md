# FastReAct Nano v2.1 - SiliconFlow 快速开始指南

## 📋 配置已完成

配置文件: `config.json`
- Provider: SiliconFlow
- Model: deepseek-ai/DeepSeek-V3
- API Base: https://api.siliconflow.cn/v1

## 🚀 三步启动

### 步骤 1: 填写 API Key

编辑 `config.json` 文件，将第 4 行的：
```json
"api_key": "在此处填入你的 SiliconFlow API Key"
```

替换为：
```json
"api_key": "sk-你的真实API Key"
```

### 步骤 2: 验证配置

```bash
python3 -c "
import sys
sys.path.insert(0, 'src')
from fastreact import Config
config = Config.load()
print(f'[OK] Model: {config.llm.model}')
print(f'[OK] API Base: {config.llm.api_base}')
print(f'[OK] API Key: {config.llm.api_key[:10]}...' if config.llm.api_key else '[WARN] API Key未设置')
"
```

### 步骤 3: 启动界面

**方式 A - 使用启动脚本（最简单）**:
```bash
./start.sh
```

**方式 B - 直接启动**:

CLI 命令行界面（推荐）:
```bash
python3 -m fastreact.adapters.cli
```

HTTP API 服务器:
```bash
python3 -m fastreact.adapters.http
# 访问 http://localhost:8000
```

## 💡 使用示例

启动 CLI 后，你可以这样提问：

```
> 帮我分析当前目录的文件结构
> 读取 README.md 并总结内容
> 创建一个 Python 脚本打印 Hello World
> 列出所有 .py 文件
```

## 🔧 配置说明

如需修改配置，编辑 `config.json`：

```json
{
  "llm": {
    "model": "deepseek-ai/DeepSeek-V3",    // 模型名称
    "api_base": "https://api.siliconflow.cn/v1",  // API 地址
    "api_key": "sk-xxx",                    // 你的 API Key
    "temperature": 0.7,                      // 温度参数
    "max_tokens": 4096                       // 最大 tokens
  },
  "tools": {
    "max_file_size": 1048576,               // 最大文件大小
    "protected_paths": [],                   // 保护路径
    "exec_timeout": 30                       // 命令超时
  },
  "react": {
    "max_iterations": 20,                    // 最大迭代次数
    "max_context_tokens": 128000,            // 最大上下文
    "enable_safety": true,                   // 启用安全检查
    "strict_mode": false,                    // 严格模式
    "enable_filesystem_memory": true         // 启用文件系统记忆
  }
}
```

## 📚 其他可用模型

SiliconFlow 还支持其他模型，可在 `config.json` 中修改：

- `deepseek-ai/DeepSeek-V3` - DeepSeek V3（推荐）
- `Qwen/Qwen2.5-72B-Instruct` - 通义千问
- `meta-llama/Llama-3.1-70B-Instruct` - Llama
- `01-ai/Yi-1.5-34B-Chat` - 零一万物

## ❓ 常见问题

**Q: 如何获取 SiliconFlow API Key？**
A: 访问 https://cloud.siliconflow.cn/ 注册账号

**Q: 启动时报错 "Module not found"？**
A: 运行 `pip3 install -e .` 安装依赖

**Q: 如何切换到其他 LLM 提供商？**
A: 编辑 `config.json` 中的 `llm` 部分

**Q: CLI 界面显示乱码？**
A: macOS 可能需要安装 UTF-8 支持

## 📞 获取帮助

- 查看项目文档: `cat ../README.md`
- 运行测试: `pytest tests/ -v`
- 查看示例: `ls examples/`

---

**准备好了吗？填写 API Key 后运行 `./start.sh` 开始使用！**
