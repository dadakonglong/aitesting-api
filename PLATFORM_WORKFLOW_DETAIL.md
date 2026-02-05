# 智测未来：AI 接口测试平台全流程工作内幕

---

## 1️⃣ 需求理解与检索阶段

**输入：** 用户自然语言描述
> "为登录并获取用户信息接口生成完整的场景测试"

**处理：**
1. **主编排器 (Orchestrator)** 解析用户意图为 `generate_test`。
2. **NLU 服务** 提取核心实体：`Login`（登录）、`User Info`（用户信息）。
3. **RAG Agent** 调用向量检索工具，从 **Qdrant** 知识库中召回匹配度最高的 API 定义。

**输出：** 结构化 API 及上下文信息
```json
{
  "entities": [
    {
      "name": "登录接口",
      "path": "/api/v1/auth/login",
      "method": "POST"
    },
    {
      "name": "用户信息接口",
      "path": "/api/v1/user/profile",
      "method": "GET"
    }
  ],
  "context": "由于获取用户信息需要鉴权，登录接口返回的 Token 需通过 Authorization 头传递。"
}
```

---

## 2️⃣ 场景编排与逻辑推导阶段

**输入：** 结构化 API 信息
**处理：**
1. **场景解析器 (ScenarioParser)** 分析接口间的时序逻辑。
2. 调用 **Neo4j 知识图谱** 验证依赖路径：确认 `Profile` 接口 `DEPENDS_ON` 登录成功后的会话。
3. 建立 **参数映射 (Param Mapping)**：标记从登录响应中提取 `token` 注入到下一步。

**输出：** 结构化场景执行序列
```json
{
  "scenario_name": "登录并查看个人资料",
  "steps": [
    {
      "step": 1,
      "api": "POST /api/v1/auth/login",
      "extract": { "token_path": "$.data.token", "var": "JWT_TOKEN" }
    },
    {
      "step": 2,
      "api": "GET /api/v1/user/profile",
      "headers": { "Authorization": "Bearer {{JWT_TOKEN}}" }
    }
  ]
}
```

---

## 3️⃣ 数据与断言生成阶段

**输入：** 结构化场景执行序列
**处理：**
1. **Planner Agent** 决定测试策略：采用“正向业务流”覆盖。
2. **Data Generator** 生成智能 Mock 数据（如符合格式的用户名、密码）。
3. **Assertion Generator** 为每一步生成多层级断言（状态码、响应结构、业务逻辑）。

**输出：** 完整测试用例脚本 (TestCase JSON)
```json
{
  "test_name": "用户登录及资料查询闭环测试",
  "steps": [
    {
      "api": "/api/v1/auth/login",
      "data": { "username": "ai_tester_01", "password": "password123" },
      "assertions": [
        { "type": "status_code", "expect": 200 },
        { "type": "response_schema", "field": "data.token", "operator": "exists" }
      ]
    }
  ]
}
```

---

## 4️⃣ 测试执行引擎阶段

**输入：** 完整测试用例脚本 (TestCase JSON)
**处理：**
1. **Go 执行引擎** 接收任务并启动协程。
2. 依次发起 HTTP 请求，并实时更新 **执行上下文 (ExecutionContext)**。
3. 执行断言规则，抓取延迟、状态码及原始响应。

**输出：** 实时执行报告与指标
```json
{
  "status": "SUCCESS",
  "total_ms": 450,
  "steps_results": [
    { "step": 1, "status": "PASS", "latency": "120ms" },
    { "step": 2, "status": "PASS", "latency": "330ms" }
  ]
}
```

---

## 5️⃣ 自愈与诊断阶段 (若执行失败)

**输入：** 失败的执行记录与错误响应
**处理：**
1. **自愈专家 (Healer Agent)** 介入，分析响应体中的错误信息。
2. 分析当前接口 Schema：发现服务端已将 `token` 字段迁移到了响应根目录。
3. 生成 **修复指令 (Patch)** 并建议更新提取路径。

**输出：** 建议的修复方案
```json
{
  "failure_type": "Data Extraction Error",
  "root_cause": "The field 'token' has been moved from '$.data.token' to '$.token'.",
  "can_heal": true,
  "patch_hint": "Update extraction path to $.token"
}
```
