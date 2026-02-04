# FastReAct 集成测试套件

## 概述

这套集成测试包含四个"地狱难度"的复合测试用例，用于验证 FastReAct 的各个模块是否有机结合，而非各自为政。

## 测试用例

### 测试 1: "Audit & Fix" Loop
**跨领域"发现并修复"测试**

**测试内容**：
1. 代码库浏览 (`ls_repo` → `read_file`)
2. 互联网搜索查找文档 (`search`)
3. 精准修复 (`edit_file`)
4. RAG 验证：重启后能否记住修复决策

**验证模块**：
- ✅ 工具链协作
- ✅ RAG 持久化
- ✅ 跨域知识整合

**运行方法**：
```bash
python run_integration_tests.py --test 1
```

---

### 测试 2: "Context Stress" Test
**长对话"上下文极限剪枝"测试**

**测试内容**：
1. 喂入 50 轮垃圾对话
2. 执行复杂任务（calculator + 代码生成）
3. 验证 Token 减少 40-60%
4. 验证关键系统指令未丢失

**验证模块**：
- ✅ Context Pruning
- ✅ Token Counter
- ✅ Memory Flush
- ✅ 系统指令保留

**运行方法**：
```bash
python run_integration_tests.py --test 2
```

---

### 测试 3: "Brain Reload" Test
**跨 Session "知识迁移"测试**

**测试内容**：
1. Session A：创建复杂 Python 类，运行生成数据文件
2. 中断：彻底杀死进程
3. Session B：重启，仅凭问题找到之前的逻辑和数据

**验证模块**：
- ✅ Embedding Persistence
- ✅ 文件系统状态
- ✅ 跨会话知识检索

**运行方法**：
```bash
python run_integration_tests.py --test 3
```

---

## 快速开始

### 运行所有测试
```bash
python run_integration_tests.py
```

### 运行单个测试
```bash
python run_integration_tests.py --test 1  # 测试 1
python run_integration_tests.py --test 2  # 测试 2
python run_integration_tests.py --test 3  # 测试 3
python run_integration_tests.py --test 4  # 测试 4
python run_integration_tests.py --test 4  # 测试 4
```

### 功能检查
```bash
python run_integration_tests.py --check
```

---

## 预期结果

### 成功标准

**测试 1**：
- [ ] Agent 能发现代码问题
- [ ] Agent 能搜索到相关文档
- [ ] Agent 能精准修复代码
- [ ] 重启后能记住修复决策

**测试 2**：
- [ ] 喂入 50 轮垃圾信息
- [ ] Token 消耗减少 40-60%
- [ ] 仍能正确执行复杂任务
- [ ] 仍知道自己是什么系统

**测试 3**：
- [ ] Session A 能创建类和数据文件
- [ ] 重启后 Session B 能找到之前的信息
- [ ] Session B 能读取数据文件
- [ ] Embedding cache 有持久化数据

**测试 4**：
- [ ] 工具调用顺序合理
- [ ] ls_repo -> read_file 路径
- [ ] 数据流转正确
- [ ] 未检测到死循环
- [ ] 总分 ≥ 60%

---

## 技术细节

### 依赖的功能
- RAG Persistence（Embedding 持久化）
- Context Pruning（上下文剪枝）
- Token Counter（Token 计数）
- Memory Flush（记忆刷新）
- 工具链协作

### 预计运行时间
- 测试 1: ~3-5 分钟（包含模型加载）
- 测试 2: ~2-3 分钟
- 测试 3: ~3-4 分钟
- **总计**: ~10-15 分钟

### 可能的失败原因
1. **模型加载失败**：网络问题或 ModelScope 无法访问
2. **API 配额限制**：Tavily API 配额不足
3. **Token 超限**：单次对话 Token 数超限
4. **文件权限**：无法创建/修改文件

---

## 故障排除

### 测试失败处理

1. **模型加载超时**
   ```bash
   # 检查网络连接
   ping modelscope.cn

   # 或使用本地模型
   # 修改 config.json 中的 device: "cpu"
   ```

2. **搜索功能失效**
   ```bash
   # 检查 Tavily API Key
   # 在 config.json 中查看 tools.tavily.api_key
   ```

3. **RAG 不工作**
   ```bash
   # 检查 embedding cache
   dir data\memory_embedding_cache.db

   # 如果不存在，先运行简单查询创建缓存
   python -m fastreact.cli.main shell
   ```

---

## 贡献

如果你想添加新的集成测试：

1. 创建新文件：`test_integration_4_xxx.py`
2. 实现测试函数：`async def test_xxx():`
3. 在 `run_integration_tests.py` 中注册

---

## 许可证

与 FastReAct 主项目相同。

### 测试 4: Tool Graph & Dependency Test
**工具拓扑测试**

**测试内容**：
1. 创建一个包含多个数据存储模块的测试项目
2. 给 Agent 一个模糊任务："分析所有数据存储模块的写入一致性"
3. 验证工具调用的逻辑顺序（ls_repo -> read_file）
4. 验证数据流转（file_list 是否被正确传递）
5. 验证死循环检测

**验证模块**：
- ✅ 工具调用逻辑顺序
- ✅ 数据流转正确性
- ✅ 死循环检测和跳出

**运行方法**：
```bash
python run_integration_tests.py --test 4
```

