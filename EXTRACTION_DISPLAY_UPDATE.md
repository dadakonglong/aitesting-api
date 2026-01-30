# 提取记录显示功能 - 更新说明

## 🎯 目标

在前端的"提取"标签页中显示详细的参数提取过程，让你能清楚地看到：
- Token是否被正确提取
- 从哪个步骤提取
- 提取到的具体值
- 是否提取成功

## ✅ 已完成的改进

### 1. 后端改进

在`services/ai-processing/main_sqlite.py`中添加了提取记录功能：

**改进内容：**
- ✅ 记录每个参数映射的提取过程
- ✅ 记录提取是否成功
- ✅ 记录提取到的值
- ✅ 记录错误信息（如果提取失败）

**返回的数据结构：**
```json
{
  "step_order": 2,
  "status_code": 200,
  "extractions": [
    {
      "from_step": 1,
      "from_field": "data.token",
      "to_field": "Authorization",
      "to_type": "headers",
      "success": true,
      "extracted_value": "tcaJWlkJ1Beyg3YbuFkExgyWllBZCmW0bSvUi4MB4HV...",
      "error_msg": null
    }
  ]
}
```

### 2. 调试日志

添加了详细的调试日志，在服务端终端显示：
```
DEBUG: Extracting from step 1
DEBUG: from_field = data.token
DEBUG: extracted value = tcaJWlkJ1Beyg3YbuFkExgyWllBZCmW0bSvUi4MB4HV...
DEBUG: Set header Authorization = Bearer tcaJWlkJ1Beyg3YbuFkExgyWllBZCmW0bSvUi4MB4HV...
```

## 🚀 使用方法

### 1. 重启AI服务

**必须重启才能使用新代码：**

```bash
# 停止当前服务 (Ctrl+C)

# 重新启动
cd services/ai-processing
python main_sqlite.py
```

### 2. 执行场景

在前端：
1. 选择"汇金ERP"项目
2. 进入"测试场景"页面
3. 选择一个场景
4. 点击"执行测试"

### 3. 查看提取记录

执行完成后，点击步骤展开，切换到"提取"标签页：

**你会看到：**
```
📦 参数提取

✅ 从步骤1提取
   来源字段: data.token
   目标位置: headers.Authorization
   提取的值: tcaJWlkJ1Beyg3YbuFkExgyWllBZCmW0bSvUi4MB4HV...
```

**如果提取失败：**
```
❌ 从步骤1提取
   来源字段: data.token
   目标位置: headers.Authorization
   错误: 无法从步骤1提取data.token
```

## 🔍 诊断问题

### 场景1: 提取成功但接口失败

**显示：**
```
✅ 提取成功
   提取的值: ABC123...
```

**但接口返回401或4200**

**原因：**
- Token已过期
- 或业务逻辑问题（如门店权限）

### 场景2: 提取失败

**显示：**
```
❌ 提取失败
   错误: 无法从步骤1提取data.token
```

**原因：**
- 步骤1没有返回token
- 或token字段路径不对
- 或步骤1执行失败

### 场景3: Token不匹配

**步骤1返回：** `token_A`
**步骤2提取到：** `token_B`

**原因：**
- Context保存有问题
- 或提取路径错误

## 📊 验证脚本

运行测试脚本查看提取记录：

```bash
python test_extraction_display.py
```

这会显示最近一次执行的提取记录。

## 💡 前端显示

前端的"提取"标签页已经支持显示extractions数据，格式如下：

```tsx
{res.extractions && res.extractions.length > 0 ? (
  <table>
    <thead>
      <tr>
        <th>来源步骤</th>
        <th>来源字段</th>
        <th>目标字段</th>
        <th>提取的值</th>
        <th>状态</th>
      </tr>
    </thead>
    <tbody>
      {res.extractions.map((ext, idx) => (
        <tr key={idx}>
          <td>步骤 {ext.from_step}</td>
          <td>{ext.from_field}</td>
          <td>{ext.to_type}.{ext.to_field}</td>
          <td>{ext.extracted_value}</td>
          <td>{ext.success ? '✅' : '❌'}</td>
        </tr>
      ))}
    </tbody>
  </table>
) : (
  <p>此步骤没有参数提取</p>
)}
```

## 🎯 预期效果

**正常情况：**
1. 步骤1执行成功，返回token
2. 步骤2的提取记录显示：
   - ✅ 提取成功
   - 提取的值：`token_ABC...`
3. 步骤2使用这个token执行
4. 所有步骤成功

**异常情况：**
1. 步骤1执行成功，返回token
2. 步骤2的提取记录显示：
   - ❌ 提取失败
   - 错误：无法提取
3. 步骤2没有token，执行失败

## ✅ 总结

现在你可以：
1. ✅ 看到每个步骤的提取过程
2. ✅ 确认token是否被正确提取
3. ✅ 看到提取到的具体值
4. ✅ 快速定位问题

**重启服务后，重新执行场景，就能看到详细的提取记录了！** 🎉
