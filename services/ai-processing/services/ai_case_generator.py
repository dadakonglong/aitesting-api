"""
AI 接口测试用例生成器 - 基于大模型分析接口定义，生成真实、多样的测试用例。

测试领域最佳实践：
- 正向用例：合法参数、符合业务语义的真实数据（手机号、ID、合理长度等），预期 2xx
- 边界用例：空串、最大/最小长度、0、负数、特殊字符、边界数值，验证接口边界行为
- 健壮用例：缺必填参数、类型错误（数字传字符串）、非法枚举值、格式错误，预期 4xx
- 安全用例：无鉴权、错误/过期 Token、越权参数，预期 401/403
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

# 保证日志文件写在当前文件同级目录
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_gen_debug.log")

# 用例类型中文名，保证重新生成时始终有「正向/边界/健壮/安全」等显示名
CASE_TYPE_CN = {"positive": "正向", "boundary": "边界", "robustness": "健壮", "security": "安全"}


# 系统提示：约束大模型输出结构与测试领域规则
SYSTEM_PROMPT = """你是专业的接口测试专家，负责根据接口定义生成**真实可执行**的接口测试用例。

## 输出格式（严格 JSON）
必须返回且仅返回一个 JSON 对象，形如：
{
  "cases": [
    {
      "case_type": "positive | boundary | robustness | security",
      "name": "用例名称，必须用中文类型：如 [正向] POST /api/login 正常登录、[边界] POST /api/login 空密码、[健壮] POST /api/login 缺参、[安全] POST /api/login 无鉴权。不要使用英文 [positive] 等。",
      "description": "简短说明",
      "request_template": {
        "params": {},      // 请求体（Body）
        "url_params": {},  // Query 参数
        "headers": {}      // 请求头
      },
      "expected_template": {
        "status_code": 200,
        "description": "期望结果说明：请在此包含对返回包体 (Response Body) 的断言要求（如必须包含 token 字段）",
        "response_body": {}  // 业务级断言所依赖的 Response Body 结构
      }
    }
  ]
}

## 硬性规则（请逐条严格遵守）

1. **用例类型与名称**
   - 必须覆盖：positive（正向）、boundary（边界）、robustness（健壮）、security（安全）四类。
   - `name` 必须以中文类型前缀开头，例如：
     - "[正向] POST /api/login 正常登录"
     - "[边界] POST /api/login 手机号长度为边界值"
     - "[健壮] POST /api/login 空密码"
     - "[安全] POST /api/login 无鉴权访问"

2. **请求内容 request_template（必须完整）**
   - 对于所有 POST/PUT/PATCH 且存在请求体的接口：
     - `request_template.params` **禁止为空对象 {}**。
     - 必须包含接口定义中所有必填字段，并给出**具体取值**。
   - `request_template.headers` 必须存在：
     - 有 Body 时必须包含 `Content-Type`。
     - 若接口定义中提供了示例 headers，请在此基础上进行合理简化或复用，而不是清空。
   - `request_template.url_params` 用于 Query 参数；可以为空，但字段必须存在。
   - **禁止出现以下情况：**
     - 缺少 `request_template` 字段；
     - `request_template` 中缺少 `params` / `url_params` / `headers` 任意一个字段；
     - 对于需要 Body 的接口，`params` 为空对象。

3. **HTTP 断言 expected_template.status_code（必填）**
   - 每条用例都必须包含 `expected_template.status_code`，与当前场景匹配，例如：
     - 正向：200
     - 缺参/类型错误：400
     - 无鉴权/错鉴权：401 / 403

4. **业务级断言 expected_template.response_body（必填，遵循分层断言原则）**
   - 所有用例都必须填写 `expected_template.response_body`，但需遵循「分层断言」策略，避免过度断言：

   **第一层 - 状态码字段（精确匹配，必填）**：
   - `code`/`status`/`errcode` 等数值型业务状态码 → 必须给出精确期望值
   - 示例：{"code": 0} 或 {"code": 401}

   **第二层 - 关键业务数据（存在性检查）**：
   - `data`/`token`/`userId` 等动态业务数据字段 → 使用 "非空" 表示该字段必须存在且非空
   - 示例：{"data": "非空"} 或 {"token": "非空"}
   - ⚠️ 禁止对 data/token 等动态字段猜测具体值（如 "some_valid_token"），因为这些值每次请求都不同

   **第三层 - 提示语字段（不要放入 response_body）**：
   - `message`/`msg`/`errmsg` 等提示语字段 → **禁止放入 response_body**
   - 原因：提示语可能是中文「成功」也可能是英文「success」，精确匹配必然失败导致误报
   - 如需说明期望的提示语，请写在 `expected_template.description` 中

   **正确示例**：
   - 登录成功：{"code": 0, "data": "非空"}（只断言状态码和数据存在性，不断言 message 和 token 具体值）
   - 密码错误：{"code": 401}
   - 缺少参数：{"code": 400}
   - 对于 HTTP 200 但业务失败的场景（如密码错误返回 200 + {"code": 401}），
     必须通过 `response_body` 中的 `code` 字段给出业务断言。

   **错误示例（严禁出现）**：
   - {"code": 0, "message": "成功"} ← message 字段不应出现
   - {"code": 0, "token": "some_valid_token"} ← token 不应猜测具体值，应写 "非空"
   - {"code": 0, "data": {"employeeId": 123}} ← data 内部值是动态的，应直接写 "非空"

5. **安全测试差异化（Headers 必须体现差异）**
   - 无鉴权用例：`headers` 中必须**不包含** `Authorization` 等鉴权字段。
   - 错误鉴权用例：`headers` 中必须包含无效的 `Authorization`（如 `"Authorization": "Bearer INVALID"`）。
   - 登录接口通常不需要 Authorization，请结合路径和描述智能判断是否需要安全用例。

6. **覆盖度**
   - 一次性生成 **至少 6 条** 用例，合理分配到正向、边界、健壮、安全四类。

7. **违反规则时如何处理**
   - 如果在某个场景下你无法给出合理的 `response_body`，不要返回该条用例，
     而是调整场景或改为你有把握写出业务断言的场景。
   - 如果无法为某个 POST 接口构造合理的 Body（既无 schema，也无示例），
     请少生成该接口的用例数量，但**不要返回空 params 的用例**。

只输出 JSON，本身是一个对象：{"cases": [...]}，不要使用 markdown 代码块包裹。"""


USER_PROMPT_TEMPLATE = """请为以下接口生成测试用例，需包含类型：{case_types}。

## 接口定义
- 路径: {path}
- 方法: {method}
- 摘要: {summary}
- 描述: {description}
- 参数(OpenAPI parameters): {parameters}
- 请求体(OpenAPI requestBody): {request_body}
- 请求头(OpenAPI headers): {headers}

请为每种请求类型生成至少 1 条**真实**用例。每条用例的 request_template.params 必须包含接口定义中所有必填字段的**具体取值**，且不同用例类型（正向/边界/健壮/安全）的取值应不同，以验证不同请求的不同响应。直接返回上述格式的 JSON。"""


async def generate_cases_for_endpoint(
    ai_client: Any,
    endpoint: Dict[str, Any],
    include_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    调用大模型为单个接口生成测试用例。

    :param ai_client: 具备 chat(system_prompt, user_prompt) 的 AI 客户端
    :param endpoint: 接口信息，含 path, method, summary, description, parameters, request_body 等
    :param include_types: 需要生成的类型，如 ["positive", "boundary", "robustness", "security"]
    :return: 用例列表，每项含 case_type, name, description, request_template, expected_template
    """
    if include_types is None:
        include_types = ["positive", "boundary", "robustness", "security"]
    case_types_str = "、".join(include_types)

    path = endpoint.get("path") or ""
    method = (endpoint.get("method") or "GET").upper()
    summary = endpoint.get("summary") or ""
    description = endpoint.get("description") or ""
    parameters = endpoint.get("parameters")
    if not isinstance(parameters, (list, dict)):
        parameters = []
    request_body = endpoint.get("request_body")
    if not isinstance(request_body, dict):
        request_body = {}

    parameters_str = json.dumps(parameters, ensure_ascii=False, indent=2)
    request_body_str = json.dumps(request_body, ensure_ascii=False, indent=2)
    headers_str = json.dumps(endpoint.get("headers") or {}, ensure_ascii=False, indent=2)

    base_user_prompt = USER_PROMPT_TEMPLATE.format(
        case_types=case_types_str,
        path=path,
        method=method,
        summary=summary or "(无)",
        description=description or "(无)",
        parameters=parameters_str,
        request_body=request_body_str,
        headers=headers_str,
    )

    # 为了避免「坏用例」直接进入执行阶段，这里增加一个简单的重试机制：
    # - 如果本次结果中「有效用例数 < 6」或全部被判为无效（无 body / 无业务断言等），
    #   则给出错误总结，附加在 prompt 里让大模型「覆盖式重写」，最多重试 3 次。
    max_retry = 3
    min_cases = 6
    last_error_summary = ""
    attempt = 0

    while True:
        attempt += 1
        # 首次直接用 base_user_prompt，重试时在末尾追加“上一次的问题”提示
        if last_error_summary:
            user_prompt = (
                f"{base_user_prompt}\n\n"
                f"====== 上一轮生成存在的问题，请严格修正后**重新完整生成 cases 列表**（覆盖式重写，不要只追加）：======\n"
                f"{last_error_summary}\n"
                f"请重新生成不少于 {min_cases} 条完全符合前述规则的用例，每条都必须包含：合理的 request_template.params（对于有请求体的接口）和非空的 expected_template.response_body。\n"
            )
        else:
            user_prompt = base_user_prompt

        try:
            result = await ai_client.chat(SYSTEM_PROMPT, user_prompt)
            # 写日志文件，包含 attempt 信息，便于观察「重复写」情况
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n\n=== {datetime.now()} [ATTEMPT {attempt}] ===\n")
                f.write(f"PROMPT:\n{user_prompt}\n")
                f.write(f"RESULT:\n{json.dumps(result, ensure_ascii=False)}\n")
            print(
                f"DEBUG: AI case generator response (attempt {attempt}): "
                f"{json.dumps(result, ensure_ascii=False)[:200]}..."
            )
        except Exception as e:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n\n=== {datetime.now()} [ERROR][ATTEMPT {attempt}] ===\n")
                f.write(f"PROMPT:\n{user_prompt}\n")
                f.write(f"EXCEPTION:\n{str(e)}\n")
            print(f"DEBUG: AI case generator exception on attempt {attempt}: {e}")
            raise RuntimeError(f"大模型调用失败: {e}") from e

        if not isinstance(result, dict):
            raise ValueError("大模型返回非 JSON 对象")

        raw_cases = result.get("cases")
        if not isinstance(raw_cases, list):
            raw_cases = []

        request_body = endpoint.get("request_body")
        if not isinstance(request_body, dict):
            request_body = {}

        # 统计本轮生成中被判为无效的原因，用于给下一轮提示
        invalid_stats_total = {
            "no_body": 0,
            "no_response_body": 0,
            "bad_case_type": 0,
        }

        out: List[Dict[str, Any]] = []
        for c in raw_cases:
            if not isinstance(c, dict):
                continue
            case_type = (c.get("case_type") or "positive").lower()
            if case_type not in include_types:
                invalid_stats_total["bad_case_type"] += 1
                continue
            name_raw = (c.get("name") or "").strip()
            # 重新生成时始终用中文显示名：若大模型返回空或英文类型名则用「正向/边界/健壮/安全」+ 方法路径
            if not name_raw or any(name_raw.startswith(f"[{t}]") for t in CASE_TYPE_CN):
                type_cn = CASE_TYPE_CN.get(case_type, case_type)
                name = f"[{type_cn}] {method} {path}".strip()
            else:
                name = name_raw
            description = c.get("description") or ""
            req_tpl = c.get("request_template")
            exp_tpl = c.get("expected_template")
            if not isinstance(req_tpl, dict):
                req_tpl = {"params": {}, "url_params": {}, "headers": {}}
            if not isinstance(exp_tpl, dict):
                exp_tpl = {"status_code": 200, "description": "", "response_body": {}}
            if "response_body" not in exp_tpl:
                exp_tpl["response_body"] = exp_tpl.get("expected_response") or {}
            if "params" not in req_tpl:
                req_tpl["params"] = {}
            if "url_params" not in req_tpl:
                req_tpl["url_params"] = {}
            if "headers" not in req_tpl:
                req_tpl["headers"] = {}
            # 对于需要 body 的接口，如果大模型未给出请求体，直接丢弃该用例，不做自动构造
            if method in ("POST", "PUT", "PATCH") and not (req_tpl.get("params") or {}):
                invalid_stats_total["no_body"] += 1
                continue
            if method in ("POST", "PUT", "PATCH") and req_tpl.get("params") and "Content-Type" not in {
                k.lower() for k in (req_tpl.get("headers") or {}).keys()
            }:
                (req_tpl.setdefault("headers", {}))["Content-Type"] = "application/json"
            # 若业务级断言为空，则丢弃该用例，避免执行阶段出现「没有业务断言」的用例
            rb = exp_tpl.get("response_body") or {}
            if not isinstance(rb, dict):
                rb = {}
            if not rb:
                invalid_stats_total["no_response_body"] += 1
                continue
            exp_tpl["response_body"] = rb
            out.append(
                {
                    "case_type": case_type,
                    "name": name,
                    "description": description,
                    "path": path,
                    "method": method,
                    "request_template": req_tpl,
                    "expected_template": exp_tpl,
                    "source": "ai",
                }
            )

        valid_count = len(out)
        # 若已满足最小数量要求，或已达到最大重试次数，则直接返回当前有效用例
        if valid_count >= min_cases or attempt >= max_retry:
            if valid_count < min_cases:
                # 写一条日志，提示仍未达到期望条数，但已用尽重试
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(
                        f"\n[{datetime.now()}] WARN: AI case generator finished after {attempt} attempts "
                        f"with only {valid_count} valid cases (<{min_cases}). "
                        f"invalid_stats={invalid_stats_total}\n"
                    )
            return out

        # 不满足数量要求且仍可重试：构造错误总结，进入下一轮
        last_error_summary = (
            f"- 有效用例数量过少：本次仅生成 {valid_count} 条符合规则的用例，"
            f"期望至少 {min_cases} 条。\n"
            f"- 过滤掉的用例统计：\n"
            f"  - 无请求体（POST/PUT/PATCH 且 params 为空）的用例数量：{invalid_stats_total['no_body']}\n"
            f"  - 无业务级断言（expected_template.response_body 为空）的用例数量：{invalid_stats_total['no_response_body']}\n"
            f"  - case_type 非预期类型（positive/boundary/robustness/security）的数量：{invalid_stats_total['bad_case_type']}\n"
        )
        # 写入日志，便于你在 ai_gen_debug.log 里看到「重复写」的提示
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"\n[{datetime.now()}] INFO: AI case generator will retry "
                f"(attempt {attempt + 1} of {max_retry}), "
                f"valid_count={valid_count}, invalid_stats={invalid_stats_total}\n"
            )
        # 继续 while True，重新调用大模型（循环顶部会用 last_error_summary 拼接新的提示）
