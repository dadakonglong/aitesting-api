# 真实问题分析

## 🎯 重要发现

经过深入验证，**Token提取和传递机制是正常的！**

### ✅ 验证结果

1. **步骤1（登录）**
   - ✅ 成功返回token
   - ✅ Token路径：`data.token`
   - ✅ Token值正确

2. **步骤2（业务接口）**
   - ✅ Authorization header正确设置
   - ✅ Token已被提取并添加"Bearer "前缀
   - ✅ 请求头：`Authorization: Bearer Un3PnI6fv2hMO1iAyQIpENup3wMCjDruqBgFabhA1li...`

3. **服务器响应**
   - ❌ 错误码：`4200`（不是HTTP 500）
   - ❌ 错误信息：`"门店授权码无效，请联系相关人员"`

## 💡 真正的问题

**这是业务逻辑错误，不是技术问题！**

### 错误码分析

- HTTP状态码：`200`（请求成功）
- 业务错误码：`4200`
- 错误信息：门店授权码无效

这说明：
1. ✅ HTTP请求成功
2. ✅ Token认证通过
3. ❌ 业务逻辑验证失败

### 为什么看起来像500错误？

从截图看，响应体中有：
```json
{
  "code": 4200,
  "message": "门店授权码无效，请联系相关人员"
}
```

前端可能把`code != 0`都显示为"服务器内部错误"。

## 🔧 解决方案

### 1. 检查业务参数

问题可能在于请求参数，而不是token：

```python
# 步骤2的请求参数
{
  "venueId": "94YTNnVUk",  # 门店ID
  "roomId": "b9e8cddc595a4fc783412d7e1d2a6d2e",
  ...
}
```

可能的原因：
- 门店ID不正确
- 房间ID不存在
- 用户没有该门店的权限
- 门店授权码过期

### 2. 单独测试接口

使用Postman或curl单独测试第2个接口：

```bash
curl -X POST "https://medev-stage.ktvsky.com/api/v3/order/open-pay" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "venueId": "94YTNnVUk",
    "roomId": "b9e8cddc595a4fc783412d7e1d2a6d2e",
    ...
  }'
```

### 3. 检查用户权限

登录的用户可能没有操作该门店的权限。

## 📊 Token提取时机说明

**Token是在执行时动态提取的：**

```python
# 执行流程
async with httpx.AsyncClient() as client:
    # 1. 执行步骤1（登录）
    step1_response = await client.post("/login", ...)
    context["step_1"] = {"response": step1_response.json()}
    
    # 2. 执行步骤2（业务接口）
    for mapping in step2.param_mappings:
        # 从context中提取token
        token = context["step_1"]["response"]["data"]["token"]
        # 设置到请求头
        request_headers["Authorization"] = f"Bearer {token}"
    
    step2_response = await client.post("/order/open-pay", 
                                      headers=request_headers, ...)
```

**不是在生成用例时提取的！**

生成用例时只是配置映射关系：
```json
{
  "from_step": 1,
  "from_field": "data.token",
  "to_field": "Authorization",
  "to_type": "headers"
}
```

## ✅ 结论

1. ✅ Token提取机制正常
2. ✅ Token传递机制正常  
3. ✅ 修复脚本已正确配置映射
4. ❌ 问题是业务逻辑错误（门店授权码无效）

**建议：**
- 检查业务参数是否正确
- 确认用户是否有门店权限
- 联系后端开发确认业务规则
