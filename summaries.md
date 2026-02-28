
## Fission-AI/OpenSpec - 2026-02-28 08:29:43 UTC

### 核心变动总结：
1. **状态命令（status）功能优化与重构**
   - 重构代码：从`validateChangeExists`中抽离出公共函数`getAvailableChanges`，作为检测变更的核心逻辑；调整`statusCommand`通过该函数提前识别无变更场景，不再抛出致命错误，而是返回友好提示（支持文本/JSON模式）并以退出码0优雅退出。
2. **文档细节修正**
   - 修复`design.md`中矛盾的设计风险描述：纠正“双读取”场景为「变更存在时发生」而非原描述的“无变更时”；
   - 在`proposal.md`中补充说明`validateChangeExists`已内部重构为委托调用`getAvailableChanges`的细节，回应对评审反馈。
3. **错误处理精细化**
   - 优化`getAvailableChanges`的错误捕获范围：仅当变更目录不存在（ENOENT错误）时返回空数组；重新抛出权限不足（EACCES）等其他文件系统错误，避免掩盖真实的系统问题。

---

## tyrchen/claude-skills - 2026-02-28 08:29:48 UTC

日常维护：更新技能相关内容

---

