# FastReAct TODO 列表

> 更新日期: 2026-02-02
> 版本: v1.0.0
> 路线图更新: 已切换到 Coding Agent 方向 (基于 How_to_improve.md)

---

## 📋 任务概览

### 已完成 (19/18)

- ✅ #5 Test Qwen3-Embedding-0.6B model
- ✅ #6 Implement Hybrid Search (BM25 + Semantic)
- ✅ #7 Implement Stage 5: Progressive Compaction
- ✅ #8 Performance optimization (分析完成)
- ✅ #9 Commit and push hybrid search code
- ✅ #10 Implement Progressive Compaction (Stage 5)
- ✅ #11 Documentation cleanup and organization
- ✅ #12 Performance optimization analysis
- ✅ #13 TokenCounter 实例复用 (1-2h, +20-30% 性能)
- ✅ #14 EmbeddingCache LRU 淘汰策略 (2-3h, +15-25% 命中率)
- ✅ #17 文档更新 - 修正过期状态标记 (30min-1h)
- ✅ #23 全面更新 ARCHITECTURE.md 架构文档 (2h)
- ✅ #24 Tool Result Pruning (1-2天, ⭐⭐⭐⭐⭐ P0)
- ✅ #25 Stateful Shell (2-3天, ⭐⭐⭐⭐⭐ P0)
- ✅ #26 Repository Map (2-3天, ⭐⭐⭐⭐ P1)
- ✅ 阶段 1-5: 所有核心功能 (100%)
- ✅ 混合搜索: BM25 + Semantic + RRF
- ✅ Qwen3 模型支持
- ✅ 文档整理和归档

### 待办 (6/20)

#### Coding Agent 核心功能 (P0-P1)
- ⬜ #27 edit_file 工具 (2-3天, ⭐⭐⭐⭐ P1)

#### 功能增强 (P0-P2)
- ⬜ #18 Tool Policy 系统 (3-5天, ⭐⭐⭐⭐⭐ P0)
- ⬜ #19 Context Pruning (2-3天, ⭐⭐⭐⭐⭐ P0)
- ⬜ #20 Tool Result Pruning (1-2天, ⭐⭐⭐⭐ P1) - 已合并到 #24
- ⬜ #21 Exec Approvals 执行审批 (2-3天, ⭐⭐⭐⭐ P1)
- ⬜ #22 Tool Display 用户友好显示 (2-3天, ⭐⭐⭐ P2)

#### 性能优化 (P2 - 暂缓)
- ⬜ #15 持久化 Embedding 缓存 (4-6h, 冷启动 +90%)
- ⬜ #16 检索结果缓存 (3-4h, 重复查询 +95%)

---

## 🎯 优先级建议 (更新于 2026-02-02)

### 🚀 新方向: Coding Agent (基于 How_to_improve.md)

**第 1 周 (P0 - 核心防护)**:
- ✅ 已完成: 架构文档更新 (#23)
- ⬜ #24 Tool Result Pruning (1-2天) ⭐⭐⭐⭐⭐
  - 防止 Context 爆炸
  - Smart Truncation (Head/Tail)
  - 最紧迫的 P0 需求

- ⬜ #25 Stateful Shell (2-3天) ⭐⭐⭐⭐⭐
  - 持久化环境
  - 目录状态保持

**预期提升**:
- 防止第一个崩溃点
- 具备基础 Coding 能力
- 总工作量: **3-5 天**

**第 2 周 (P1 - 项目感知)**:
- ⬜ #26 Repository Map (2-3天) ⭐⭐⭐⭐
- ⬜ #27 edit_file 工具 (2-3天) ⭐⭐⭐⭐

**预期提升**:
- LLM 拥有代码库"上帝视角"
- 精准代码修改
- 总工作量: **4-6 天**

### 原有优化任务 (暂缓)

以下任务暂时延后，优先完成 Coding Agent 核心功能:
- ⬜ #15 持久化 Embedding 缓存 (4-6h)
- ⬜ #16 检索结果缓存 (3-4h)
- ⬜ #18 Tool Policy 系统 (3-5天)
- ⬜ #19 Context Pruning (2-3天)
- ⬜ #21 Exec Approvals (2-3天)
- ⬜ #22 Tool Display (2-3天)

### 长期优化 (1 个月)

**第 4 周**:
- #15 持久化 Embedding 缓存 (4-6 小时)

**后续优化**:
- 数据库连接池
- 异步任务队列
- BM25 索引优化

**预期提升**:
- 冷启动加速 90%+
- 生产环境稳定性
- 总工作量: **15-20 天**

---

## 📊 进度跟踪

### 当前状态 (2026-02-02)

| 类别 | 已完成 | 待办 | 总计 | 完成度 |
|------|--------|------|------|--------|
| 核心功能 | 5 | 0 | 5 | **100%** ✅ |
| 性能优化 | 3 | 2 | 5 | **60%** (暂缓) |
| 文档更新 | 3 | 0 | 3 | **100%** ✅ |
| Coding Agent | 3 | 1 | 4 | **75%** 🆕 |
| 功能增强 | 0 | 5 | 5 | **0%** |
| **总计** | **14** | **9** | **23** | **61%** |

**状态说明**:
- ✅ 基础架构完成 (Token 管理, 记忆检索, 渐进压缩)
- 🆕 切换到 Coding Agent 方向 (基于 How_to_improve.md)
- ⏸️ 性能优化任务暂缓 (#15, #16)

### 目标设定 (更新)

| 里程碑 | 目标 | 截止日期 | 状态 |
|--------|------|----------|------|
| **M1: 基础优化** | 完成 #13-17, #23 | 1 周 | ✅ 已完成 |
| **M2: Coding Agent** | 完成 #24-27 | 2-3 周 | 🆕 已启动 |
| **M3: 生产就绪** | 所有任务完成 | 1 个月 | ⏸️ 计划调整中 |

---

## 🚀 开始建议

### 立即开始 (今天)

```bash
# 1. 持久化 Embedding 缓存
Task #15: SQLite 持久化缓存 (4-6h)

# 2. 检索结果缓存
Task #16: LRU 结果缓存 (3-4h)
```

### 本周完成

```bash
# ✅ 已完成的任务
✅ #17 修正文档 (30 分钟)
✅ #13 TokenCounter 复用 (1-2 小时)
✅ #14 LRU 淘汰 (2-3 小时)
✅ #23 架构文档 (2 小时)

# 🔄 进行中的任务
⏳ #15 持久化缓存 (4-6 小时)
⏳ #16 检索缓存 (3-4 小时)
```

### 本月目标

```
Week 1: 快速优化 (#13-17) → 性能提升 30-40%
Week 2-3: 关键功能 (#18-22) → 达到 Moltbot 90%+
Week 4: 长期优化 (#15) → 冷启动 +90%
```

---

## 💡 工作量估算

| 任务 | 工作量 | 价值 | 优先级 | 状态 |
|------|--------|------|--------|------|
| #17 文档更新 | 0.5-1h | 中 | P0 | ✅ 完成 |
| #13 TokenCounter | 1-2h | 高 | P0 | ✅ 完成 |
| #14 LRU 淘汰 | 2-3h | 高 | P0 | ✅ 完成 |
| #23 架构文档 | 2h | 高 | P0 | ✅ 完成 |
| #24 Tool Pruning | 1-2d | **极高** | **P0** | ✅ 完成 |
| #25 Stateful Shell | 2-3d | **极高** | **P0** | ✅ 完成 |
| #26 Repository Map | 2-3d | **极高** | **P1** | ✅ 完成 |
| #16 检索缓存 | 3-4h | 高 | P1 | ⬜ 待办 |
| #20 结果修剪 | 1-2d | 高 | P1 | ⬜ 待办 |
| #15 持久化缓存 | 4-6h | 中 | P2 | ⬜ 待办 |
| #18 Tool Policy | 3-5d | **极高** | **P0** | ⬜ 待办 |
| #19 Context Pruning | 2-3d | **极高** | **P0** | ⬜ 待办 |
| #21 Exec Approvals | 2-3d | 高 | P1 | ⬜ 待办 |
| #22 Tool Display | 2-3d | 中 | P2 | ⬜ 待办 |

**总计**: **15-20 人天** (约 3-4 周)

---

## 🎓 学习资源

### Moltbot 参考

- [Moltbot Skills 文档](D:\moltbot\docs\tools\skills.md)
- [Tool Policy 实现](D:\moltbot\src\agents\tool-policy.ts)
- [Context Pruning](D:\moltbot\src\agents\pi-extensions\context-pruning.ts)
- [Tool Display](D:\moltbot\src\agents\tool-display.ts)

### FastReAct 架构

- [架构对比分析](D:\FastReAct\docs\architecture-comparison-moltbot.md)
- [项目完成报告](D:\FastReAct\docs\PROJECT_COMPLETION_REPORT.md)
- [当前状态](D:\FastReAct\docs\current-status.md)

---

## 📞 协作建议

### 推荐顺序

**单人开发** (3-4 周):
1. Week 1: #17 → #13 → #14 → #16
2. Week 2-3: #18 → #19
3. Week 4: #20 → #21 → #22 → #15

**双人协作** (2 周):
- **开发者 A**: #13-16 (性能优化)
- **开发者 B**: #18-19 (关键功能)
- 合并: #20-22 (用户体验)

### 代码审查要点

- [ ] 遵循 FastReAct 代码规范
- [ ] 添加完整的类型注解
- [ ] 编写单元测试
- [ ] 更新相关文档
- [ ] 性能基准测试

---

## 📝 详细任务说明

### 性能优化任务

#### #13: TokenCounter 实例复用
**问题**: retriever.py:170 每次分块创建新实例
**解决**: 使用成员变量缓存实例
**收益**: 分块性能 +20-30%

#### #14: EmbeddingCache LRU 淘汰
**问题**: FIFO 淘汰效率低
**解决**: 使用 OrderedDict 实现 LRU
**收益**: 缓存命中率 +15-25%

#### #15: 持久化 Embedding 缓存
**问题**: 重启后缓存丢失
**解决**: SQLite 持久化
**收益**: 冷启动 +90%

#### #16: 检索结果缓存
**问题**: 每次重新检索
**解决**: LRU 结果缓存
**收益**: 重复查询 +95%

### 功能增强任务

#### #18: Tool Policy 系统
**功能**: Allow/Deny/Profile
**重要性**: ⭐⭐⭐⭐⭐ (安全关键)
**参考**: Moltbot tool-policy.ts

#### #19: Context Pruning
**功能**: 智能剪枝，减少 40-60% token
**重要性**: ⭐⭐⭐⭐⭐ (性能关键)
**参考**: Moltbot context-pruning.ts

#### #20: Tool Result Pruning
**功能**: 优化工具结果，减少 50-70% token
**重要性**: ⭐⭐⭐⭐

#### #21: Exec Approvals
**功能**: Deny/Allow/Ask 审批机制
**重要性**: ⭐⭐⭐⭐ (安全关键)

#### #22: Tool Display
**功能**: 用户友好的工具调用显示
**重要性**: ⭐⭐⭐ (体验提升)

---

**维护者**: FastReAct Team
**最后更新**: 2026-02-02
**状态**: ✅ 已创建 TODO 列表
