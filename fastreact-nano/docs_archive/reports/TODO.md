# FastReAct Nano - TODO List

**Last Updated**: 2025-02-18
**Status**: Phase 1 Complete | Phase 1.5 In Progress

---

## ✅ Phase 1: 基础功能 (已完成)

**目标**: 修复基础问题 + 预留架构升级空间

- [x] 输入队列机制 (asyncio.Queue)
- [x] 优雅中断机制 (control messages)
- [x] 移除硬编码 "stop" 命令
- [x] MCP 配置加载
- [x] Workspace 隔离 (multitenant mode)
- [x] API 端点增强 (/api/tools, /api/mcp/servers)
- [x] 文档完整 (SKILLS_AND_MCP.md)

**状态**: ✅ 生产就绪
**交付日期**: 2025-02-18

---

## 🔧 Phase 1.5: ReAct 循环稳定化 (进行中)

**目标**: 把 agent.py 打造成铜墙铁壁，确保 95% 场景稳定可靠

### 1.1 核心代码审计
- [ ] **工具崩溃 (Tool Failure)**: 审计异常处理机制
- [ ] **上下文爆炸 (Context Overflow)**: 审计 token 限制和截断策略
- [ ] **死循环 (Infinite Loop)**: 审计 max_steps 强制执行
- [ ] **格式幻觉 (JSON Hallucination)**: 审计 JSON 解析鲁棒性

### 1.2 边界情况处理
- [ ] 工具调用失败重试机制
- [ ] LLM 超时处理
- [ ] 死循环检测
- [ ] 上下文窗口溢出处理

### 1.3 事件流完整性
- [ ] 所有事件正确发送
- [ ] 错误事件包含足够信息
- [ ] session_end 总是发送

### 1.4 多轮对话
- [ ] history 正确传递
- [ ] session_id 持久化
- [ ] 上下文截断策略

### 1.5 MCP 工具稳定性
- [ ] 工具启动失败处理
- [ ] 工具超时处理
- [ ] 工具隔离模式验证

**预估时间**: 3-5 天
**优先级**: 🔥 最高
**状态**: 🚧 审计中

---

## 🚀 Phase 2A: Plan Mode (待启动)

**触发**: 假期后，和团队一起研究
**依赖**: 无（独立功能）

### 功能清单
- [ ] **Plan Detection**: 复杂任务识别逻辑
  - 查询长度阈值
  - 工具调用数量阈值
  - 用户明确触发关键词

- [ ] **Planner Component**: 生成执行计划
  - LLM 生成步骤列表
  - 估算执行时间
  - 识别依赖关系

- [ ] **Plan Executor**: 按步骤执行
  - 顺序执行步骤
  - 中断检查
  - 保存执行状态

- [ ] **Plan Persistence**: 可恢复执行
  - 保存 plan 到磁盘
  - 从中断点恢复
  - Plan 状态管理

- [ ] **Plan UI**: 可视化界面
  - 显示 plan 步骤
  - 进度条
  - 手动跳过/重试步骤

**预估时间**: 1-2 周
**技术复杂度**: ⭐⭐⭐⭐
**状态**: ⏳ 待研究

---

## 🔒 Phase 2B: 高级多租户 (待启动)

**依赖**: 无（独立功能，与 Phase 2A 平行）

### 功能清单
- [ ] **Tool Permission Scoping**: 权限控制
  ```python
  user.permissions = {
      "fs_read": ["~/workspace/*"],
      "fs_write": ["~/workspace/tmp/*"],
      "exec": False,
      "mcp_servers": ["graphrag"],
  }
  ```

- [ ] **Sandboxed Workspace**: 沙箱隔离
  - 每用户独立工作目录
  - 资源限制 (CPU, 内存)
  - 网络隔离

- [ ] **Resource Manager**: 资源管理
  - 并发会话限制
  - 工具实例池
  - 使用量统计

- [ ] **Permission UI**: 权限管理界面
  - 用户权限配置
  - 审计日志
  - 使用量监控

**预估时间**: 1 周
**技术复杂度**: ⭐⭐⭐
**状态**: ⏳ 待启动

---

## 🎨 Frontend 改进 (待启动)

### 主题统一
- [ ] **站点级 Theme Provider**: 统一全站主题
  - 当前: Chat 页面有独立 theme
  - 目标: Admin/Marketplace 页面共享 theme
  - 实现: 提升 ThemeProvider 到 layout 层级

### 导航栏优化
- [ ] **导航栏融合**: 移除生硬的浮动导航
  - 当前: 导航栏浮动在 chat 顶部
  - 目标: 融合进 chat 页面顶栏
  - 实现: 调整 chat-layout 结构

### 交互改进
- [ ] **快捷键优化**: 避免输入法误触发
  - 当前: Enter 发送 (输入法输入英文时误触发)
  - 目标: Ctrl+Enter 发送，Enter 换行
  - 实现: 修改 ChatInput 组件 onKeyDown 逻辑

**预估时间**: 2-3 天
**状态**: ⏳ 待启动

---

## 📝 文档任务

### 核心文档
- [x] SKILLS_AND_MCP.md (架构指南)
- [x] IMPLEMENTATION_SUMMARY_PHASE1.md (Phase 1 总结)
- [ ] CLAUDE.md (更新当前状态)
- [ ] TODO.md (本文档)

### API 文档
- [ ] WebSocket 协议规范
- [ ] REST API 参考
- [ ] MCP 工具集成指南

### 用户文档
- [ ] 快速开始指南
- [ ] 配置说明
- [ ] 部署指南
- [ ] 故障排除

---

## 🐛 已知问题

### Agent 核心
- [ ] 工具崩溃时的行为未定义
- [ ] 上下文溢出保护机制未验证
- [ ] 死循环检测未测试
- [ ] JSON 解析失败处理未实现

### Gateway
- [ ] 队列满时的消息丢失风险
- [ ] 后台任务异常未捕获

### Frontend
- [ ] 主题不统一 (chat vs admin/marketplace)
- [ ] 导航栏布局问题
- [ ] 快捷键误触发

---

## 📊 进度追踪

### 代码统计
- **总行数**: 5,592
- **核心 (Brain)**: 180 行
- **Agent (Body)**: ~985 行
- **测试覆盖率**: 待统计

### 里程碑
- [x] v2.1.0 - Phase 1 完成 (2025-02-18)
- [ ] v2.2.0 - Phase 1.5 完成 (预计 2025-02-23)
- [ ] v2.3.0 - Phase 2A/B 完成 (预计 2025-03)
- [ ] v3.0.0 - 生产就绪版本 (待定)

---

## 🎯 下一步行动

**立即执行** (本周):
1. 完成核心代码审计 (4 个隐患)
2. 修复发现的问题
3. 添加测试用例

**短期计划** (本月):
4. 完成 Phase 1.5 所有检查项
5. 前端改进 (theme + 导航 + 快捷键)
6. 文档完善

**长期计划** (下月):
7. Phase 2A: Plan Mode 研究
8. Phase 2B: 高级多租户
9. 生产环境部署

---

## 📌 备注

- **计划 ≠ 承诺**: TODO 列表是目标集合，具体实施根据实际情况调整
- **优先级动态调整**: 根据用户反馈和实际需求调整优先级
- **技术债务记录**: 记录所有已知问题和改进建议
- **持续更新**: 每完成一个里程碑及时更新状态

---

**维护者**: Claude Code + User
**最后更新**: 2025-02-18
