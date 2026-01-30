# 新增功能使用说明（http://localhost:3000）

## 1. 接口测试计划（API Planner + 执行 + 报告）

**入口**：顶部导航 **API管理** → 第三个 Tab **「接口测试计划」**。

**步骤**：

1. **选项目**  
   左上/项目选择器里选好当前项目（例如「H5点歌台」）。该 Tab 会显示「当前项目：xxx」。

2. **先有接口**  
   若该项目下还没有接口，请先在 **「数据导入」** Tab 里导入 Swagger/OpenAPI（如 `Swagger_Api_H5.json`），再回到「接口测试计划」。

3. **生成测试计划**  
   - 可选：在「用例类型」里填写要生成的类型，默认 `positive,boundary,robustness,security`。  
   - 点击 **「生成测试计划」**。  
   - 页面会显示：共 x 个接口、x 条用例；可展开「查看计划中的接口与用例数」。

4. **执行计划**  
   - 在 **「接口 Base URL」** 里填写被测服务的根地址（例如 `https://your-api.com` 或 `http://localhost:8080`）。  
   - 若项目已在 **项目设置 → 环境** 里配置了 base_url，可不填，后端会尝试用环境配置。  
   - 点击 **「执行计划」**。  
   - 执行结束后会显示：**执行结果 #id**、总数/通过/失败、按用例类型统计。

5. **失败分析（API Healer）**  
   - 当有失败时，会出现 **「失败分析（AI 建议）」** 按钮。  
   - 点击后调用 AI 分析失败原因，并展示：失败类型、根因、修复建议、`patch_hint`。  
   - 若为**场景用例**执行（test_case_id > 0），可在「测试场景」里对该用例使用 **「应用修复」** 自动改步骤（见下）。

---

## 2. 失败用例自愈（Healer 应用修复）

**适用**：仅对**场景用例**（由「测试中心 → AI生成 / 测试场景」生成的用例）生效。

**方式一：在页面上（若已接好入口）**  
- 测试中心 → 测试场景 → 对某条场景执行后，若失败且前端有 **「应用修复」** 按钮，点击即可把该次执行的 `execution_id` 和对应 `test_case_id` 传给后端，自动改步骤并写入 DB。

**方式二：用接口直接调**  
- 执行场景后，从返回或「执行记录」里拿到 `execution_id` 和该场景对应的 `test_case_id`。  
- 调用：

```http
POST /api/v1/heal/apply
Content-Type: application/json

{
  "test_case_id": 5,
  "execution_id": 123
}
```

- 后端会根据该次执行结果做分析并修改该场景用例的 steps，同时写入 `healing_records` 表。

**仅分析、不修改**（任意执行都可用）：

```http
POST /api/v1/heal/analyze
Content-Type: application/json

{
  "execution_id": 123,
  "step_index": 0
}
```

- 不传 `step_index` 则分析所有失败步骤；传则只分析第几步（从 0 开始）。

---

## 3. 功能入口汇总

| 功能           | 页面入口                         | 说明 |
|----------------|----------------------------------|------|
| 接口测试计划   | API管理 → 接口测试计划           | 生成计划、填 base_url、执行、看报告、失败分析 |
| 数据导入       | API管理 → 数据导入               | 导入 Swagger/OpenAPI，导入条数会正确显示 |
| API 列表       | API管理 → API列表                | 查看/编辑/单接口执行 |
| 场景 + 执行    | 测试中心 → AI生成 / 测试场景      | 创建场景、生成场景用例、执行场景 |
| 应用修复       | 需 test_case_id + execution_id   | 当前可通过接口调用；前端入口可后续在「测试场景」里加 |

---

## 4. 环境与后端

- 前端：`http://localhost:3000`（Next.js）。  
- 后端：确保 `NEXT_PUBLIC_AI_API_URL` 指向同一套后端（如 `http://localhost:8000`），即跑 `python services/ai-processing/main_sqlite.py` 的那台。  
- 失败分析/应用修复会调 AI（OpenAI 或 DeepSeek），需在 `.env` 里配置好对应 API Key。
