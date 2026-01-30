# 🚀 场景执行500错误 - 快速修复指南

## ⚡ 5分钟快速修复

### 步骤1：运行修复脚本（1分钟）

```bash
python fix_scenario_500_error.py
```

**输出示例：**
```
✅ 已移除步骤1的错误映射
✅ 已添加token映射（步骤2/3/4）
✅ 修复完成!
```

### 步骤2：验证修复（1分钟）

```bash
python diagnose_scenario_execution.py
```

**检查输出：**
- ✅ 步骤1: 无参数映射
- ✅ 步骤2/3/4: 从步骤1的data.token -> headers.Authorization

### 步骤3：重新执行测试（3分钟）

1. 打开前端测试中心
2. 选择场景
3. 点击"执行测试"
4. 查看结果

**预期结果：**
```
✅ 步骤1: 200 (登录成功)
✅ 步骤2: 200 (业务成功)
✅ 步骤3: 200 (业务成功)
✅ 步骤4: 200 (业务成功)
```

---

## 🔍 问题原因（1句话）

AI生成的配置错误：步骤1引用自己的token（不可能），步骤2/3/4缺少token映射。

---

## 🛠️ 手动修复（如果脚本失败）

### 修复前（错误）：
```json
步骤1: {
  "param_mappings": [
    {"from_step": 1, "from_field": "data.token", ...}  // ❌ 自引用
  ]
}

步骤2: {
  "param_mappings": []  // ❌ 缺少token映射
}
```

### 修复后（正确）：
```json
步骤1: {
  "param_mappings": []  // ✅ 移除自引用
}

步骤2: {
  "param_mappings": [
    {
      "from_step": 1,              // ✅ 从步骤1获取
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers"
    }
  ]
}
```

---

## ❓ 常见问题

### Q1: 修复后仍然500？

**检查token路径：**
```bash
python fix_scenario_500_error.py
# 查看输出的"Token提取分析"部分
```

如果token不在`data.token`，需要调整：
```python
# 在数据库中手动修改
"from_field": "你的实际token路径"
```

### Q2: 如何确认token正确传递？

查看执行日志中的`request_headers`：
```json
{
  "Authorization": "Bearer appyG0UXy/g0rmbaotA5a9dGYkGN..."
}
```

### Q3: 单独执行为什么没问题？

单独执行时你手动提供了token，场景执行依赖自动映射。

---

## 📞 仍需帮助？

1. 查看详细分析：`ISSUE_ANALYSIS_500_ERROR.md`
2. 查看完整方案：`SOLUTION_SUMMARY.md`
3. 运行诊断工具：`python diagnose_scenario_execution.py`

---

## ✅ 修复确认清单

- [ ] 运行修复脚本
- [ ] 验证配置正确
- [ ] 重新执行场景
- [ ] 所有步骤返回200
- [ ] 检查业务数据正确

**完成后，问题解决！** 🎉
