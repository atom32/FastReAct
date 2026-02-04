# WSL MCP 快速开始指南

## ⚠️ 当前状态

检测到 WSL 中**未安装 Python**。

## 🚀 快速解决（3 步）

### 步骤 1: 设置 WSL 环境

**方法 A: 自动安装（推荐）**
```powershell
# 双击运行或执行：
test_docs\setup_wsl_env.bat
```

**方法 B: 手动安装**
```bash
# 打开 WSL 终端
wsl

# 在 WSL 中运行：
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install mcp --user

# 退出 WSL
exit
```

### 步骤 2: 验证安装

```powershell
# 检查 Python 是否安装
wsl python3 --version

# 应该看到类似：Python 3.x.x
```

### 步骤 3: 测试 MCP 连接

```powershell
# 运行测试
python test_wsl_mcp.py
```

## 📝 详细说明

### 为什么需要 WSL？

Windows 上的 anyio 库与 asyncio 存在兼容性问题，导致 MCP SDK 无法正常工作。
WSL 提供了一个完整的 Linux 环境，完全兼容 MCP SDK。

### 架构说明

```
┌─────────────────────────────────────┐
│  Windows (PowerShell/CMD)           │
│                                      │
│  FastReAct ──┐                       │
│              │                       │
│              │ wsl command           │
│              ▼                       │
└──────────────┼──────────────────────┘
               │
               │ stdio bridge
               │
┌──────────────┼──────────────────────┐
│  WSL Linux                         │
│              │                      │
│              ▼                      │
│  MCP Server (stdio)                │
│    - calculate_total_reimbursement  │
│    - generate_audit_code            │
└──────────────────────────────────────┘
```

## 🔧 配置文件

`config.json` 中的 MCP 配置：
```json
{
  "mcp": {
    "enabled": true,
    "servers": {
      "apollo_core": {
        "command": "wsl",
        "args": [
          "python3",
          "/mnt/d/FastReAct/test_docs/mcp_server_apollo.py"
        ]
      }
    }
  }
}
```

## 🎯 使用方法

### 方法 1: 自动模式（推荐）

直接在 FastReAct 中使用，MCP server 会自动启动：

```powershell
python -m fastreact.cli.main shell
```

输入查询：
```
根据公司差旅规定，我下周要去北京出差 15 天。
北京的日补贴是 800 元。请帮我：
1. 计算总补贴金额
2. 如果金额超过一万，请调用审计工具生成核销码
```

### 方法 2: 手动模式（调试用）

**终端 1 - 启动 MCP server:**
```powershell
wsl
cd /mnt/d/FastReAct/test_docs
python3 mcp_server_apollo.py
```

**终端 2 - 运行 FastReAct:**
```powershell
python -m fastreact.cli.main shell
```

## ⚠️ 常见问题

### Q: `python3: command not found`
**A:** 运行 `test_docs\setup_wsl_env.bat` 安装 Python

### Q: `wsl: command not found`
**A:** 安装 WSL：
```powershell
wsl --install
```
然后重启计算机

### Q: MCP 连接超时
**A:**
1. 检查 WSL 中的 server 是否运行
2. 手动测试：
   ```powershell
   wsl python3 /mnt/d/FastReAct/test_docs/mcp_server_apollo.py
   ```

### Q: 权限错误
**A:** 在 WSL 中使用 `sudo`：
```bash
sudo apt install python3 python3-pip
```

## 📚 相关文件

| 文件 | 说明 |
|------|------|
| `test_docs/setup_wsl_env.bat` | 自动安装脚本（Windows） |
| `test_docs/install_wsl_python.sh` | 安装脚本（WSL） |
| `test_docs/mcp_server_apollo.py` | MCP server |
| `test_wsl_mcp.py` | 连接测试 |
| `config.json` | FastReAct 配置 |

## ✅ 验证成功

运行测试后应该看到：
```
[OK] calculate_total_reimbursement called
[OK] generate_audit_code called
[OK] Correct result (12000)
[OK] Audit code generated

Score: 4/4

[SUCCESS] WSL MCP connection works perfectly!
```

## 🎉 下一步

1. 安装 WSL Python 环境（运行 `test_docs\setup_wsl_env.bat`）
2. 测试连接（运行 `python test_wsl_mcp.py`）
3. 开始使用 REPL（运行 `python -m fastreact.cli.main shell`）

---

**这就是完整的 WSL + MCP 解决方案！**
