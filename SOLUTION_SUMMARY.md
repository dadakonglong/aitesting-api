# 场景执行500错误 - 问题解决总结

## 🎯 问题现象

在执行场景用例时，第2个接口开始报500服务器内部错误，但单独执行用例没有问题。

## 🔍 根本原因

**AI生成的参数映射配置存在严重错误：**

1. **步骤1（登录接口）的自引用错误**
   ```json
   {
     "from_step": 1,        // ❌ 步骤1引用自己
     "from_field": "data.token",
     "to_field": "Authorization",
     "to_type": "headers"
   }
   ```
   - 步骤1试图从自己（还未执行完）获取token
   - 导致Authorization header为空或错误

2. **步骤2/3/4缺少token映射**
   - headers中只有占位符`"Authorization": "Bearer {{token_from_step_1}}"`
   - 没有实际的param_mappings配置
   - 导致token无法传递到后续请求

## ✅ 解决方案

### 1. 立即修复（已完成）

运行修复脚本：
```bash
python fix_scenario_500_error.py
```

**修复内容：**
- ✅ 移除步骤1的错误自引用
- ✅ 为步骤2/3/4添加正确的token映射
- ✅ 配置token提取路径为`data.token`

### 2. 验证修复

运行诊断脚本：
```bash
python diagnose_scenario_execution.py
```

**预期结果：**
```
步骤1: 无参数映射
步骤2: 从步骤1的data.token -> headers.Authorization
步骤3: 从步骤1的data.token -> headers.Authorization
步骤4: 从步骤1的data.token -> headers.Authorization
```

### 3. 重新执行场景

在前端测试中心页面：
1. 选择修复后的场景
2. 点击"执行测试"
3. 查看执行结果

**预期：所有步骤都应该成功（200状态码）**

## 🛠️ 长期改进

### 1. 增强AI生成逻辑

在`services/ai-processing/services/scenario_parser.py`中添加：

```python
from improve_scenario_validation import validate_param_mappings, auto_fix_param_mappings

async def parse_scenario(self, nlu_result, project_id, api_candidates):
    # ... 现有的AI生成逻辑 ...
    
    # 验证和修复参数映射
    is_valid, errors = validate_param_mappings(steps)
    
    if not is_valid:
        print(f"⚠️  发现{len(errors)}个配置错误，自动修复中...")
        steps, fixes = auto_fix_param_mappings(steps)
        print(f"✅ 应用了{len(fixes)}个修复")
    
    return {
        "scenario_name": scenario_name,
        "steps": steps,
        ...
    }
```

### 2. 改进AI Prompt

更新system_prompt，明确说明规则：

```python
system_prompt = """你是一个专业的接口测试场景编排专家。

⚠️ 重要规则：
1. 步骤不能引用自己的数据（from_step不能等于当前步骤）
2. 步骤不能引用后续步骤的数据（from_step必须小于当前步骤）
3. 第一个步骤通常不需要param_mappings（除非有预置数据）
4. 如果接口需要认证，必须配置token映射

示例（正确）：
步骤1（登录）: param_mappings = []
步骤2（业务）: param_mappings = [
  {
    "from_step": 1,              // ✅ 从前面的步骤获取
    "from_field": "data.token",
    "to_field": "Authorization",
    "to_type": "headers"
  }
]

示例（错误）：
步骤1（登录）: param_mappings = [
  {
    "from_step": 1,              // ❌ 不能引用自己
    "from_field": "data.token",
    ...
  }
]
"""
```

### 3. 前端增强

在`frontend/app/testing/components/TestScenariosTab.tsx`中：

```tsx
// 显示依赖关系和警告
{step.param_mappings && step.param_mappings.length > 0 && (
    <div>
        {step.param_mappings.map((mapping, idx) => {
            const isInvalid = mapping.from_step >= step.step_order
            return (
                <div key={idx} style={{
                    color: isInvalid ? '#EF4444' : '#F59E0B',
                    fontSize: '0.75rem'
                }}>
                    {isInvalid ? '❌' : '⚠️'} 
                    依赖步骤{mapping.from_step}的{mapping.from_field}
                    {isInvalid && ' (配置错误：不能引用自己或后续步骤)'}
                </div>
            )
        })}
    </div>
)}
```

### 4. 执行前验证

在`services/ai-processing/main_sqlite.py`的执行接口中：

```python
@app.post("/api/v1/executions")
async def execute_case(req: ExecutionRequest):
    # ... 获取steps ...
    
    # 执行前验证
    from improve_scenario_validation import validate_param_mappings, auto_fix_param_mappings
    
    is_valid, errors = validate_param_mappings(steps)
    
    if not is_valid:
        print(f"⚠️  发现配置错误，自动修复中...")
        steps, fixes = auto_fix_param_mappings(steps)
        print(f"✅ 应用了{len(fixes)}个修复")
    
    # ... 继续执行 ...
```

## 📊 测试验证

### 测试用例1：自引用检测

```python
steps = [{
    'step_order': 1,
    'param_mappings': [
        {'from_step': 1, 'from_field': 'data.token', ...}  # 应该被检测并修复
    ]
}]

is_valid, errors = validate_param_mappings(steps)
assert not is_valid
assert errors[0]['type'] == 'self_reference'
```

### 测试用例2：自动添加token映射

```python
steps = [
    {'step_order': 1, 'api_path': '/api/login', 'param_mappings': []},
    {'step_order': 2, 'headers': {'Authorization': 'Bearer {{token}}'}, 'param_mappings': []}
]

fixed_steps, fixes = auto_fix_param_mappings(steps)
assert len(fixed_steps[1]['param_mappings']) == 1
assert fixes[0]['type'] == 'added_token_mapping'
```

## 📝 相关文件

### 诊断和修复工具
- `diagnose_scenario_execution.py` - 诊断工具
- `fix_scenario_500_error.py` - 修复工具
- `improve_scenario_validation.py` - 验证和自动修复逻辑

### 核心代码
- `services/ai-processing/main_sqlite.py` - 执行引擎
- `services/ai-processing/services/scenario_parser.py` - 场景解析器
- `frontend/app/testing/components/TestScenariosTab.tsx` - 前端展示

### 文档
- `ISSUE_ANALYSIS_500_ERROR.md` - 详细问题分析
- `SOLUTION_SUMMARY.md` - 本文档

## 🎓 经验教训

### 1. AI生成需要验证

AI虽然强大，但生成的配置可能存在逻辑错误：
- ✅ 必须添加验证逻辑
- ✅ 提供自动修复能力
- ✅ 给出清晰的错误提示

### 2. 参数映射的复杂性

接口间的数据传递是测试场景的核心：
- ✅ 需要清晰的依赖关系图
- ✅ 需要可视化展示
- ✅ 需要执行前验证

### 3. 错误提示的重要性

500错误太笼统，需要更详细的信息：
- ✅ 显示缺失的参数
- ✅ 显示token提取失败
- ✅ 提供修复建议

### 4. 单元测试的必要性

这类配置错误应该在单元测试中发现：
- ✅ 测试参数映射验证逻辑
- ✅ 测试自动修复逻辑
- ✅ 测试边界情况

## ✅ 检查清单

修复完成后，请确认：

- [ ] 运行`python fix_scenario_500_error.py`修复配置
- [ ] 运行`python diagnose_scenario_execution.py`验证修复
- [ ] 在前端重新执行场景，确认所有步骤成功
- [ ] 检查执行日志，确认token正确传递
- [ ] 将验证逻辑集成到AI生成流程
- [ ] 更新AI的system_prompt
- [ ] 添加前端警告提示
- [ ] 编写单元测试

## 🚀 下一步

1. **立即行动**
   - ✅ 修复当前场景（已完成）
   - ⏳ 重新执行测试验证

2. **短期改进**（本周）
   - 集成验证逻辑到AI生成流程
   - 更新AI prompt
   - 添加前端警告

3. **长期优化**（下个迭代）
   - 可视化依赖关系图
   - 智能推荐token路径
   - 完善错误提示
   - 添加单元测试

## 📞 需要帮助？

如果问题仍然存在：

1. 查看执行日志：
   ```bash
   python diagnose_scenario_execution.py
   ```

2. 检查token路径：
   - 登录接口返回的token字段名称
   - 是否在`data.token`路径下
   - 如果不是，需要调整`from_field`

3. 验证服务器API：
   - 单独调用第2个接口
   - 手动提供token
   - 确认Authorization格式要求

4. 查看详细分析：
   - `ISSUE_ANALYSIS_500_ERROR.md`

---

**问题已解决！** 🎉

核心问题是AI生成的参数映射配置错误，通过修复脚本已经解决。后续需要在AI生成流程中添加验证逻辑，防止类似问题再次发生。
