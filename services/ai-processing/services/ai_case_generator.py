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


# 系统提示：约束大模型输出结构与测试领域规则
SYSTEM_PROMPT = """你是专业的接口测试专家，负责根据接口定义生成**真实可执行**的接口测试用例。

## 输出格式（严格 JSON）
必须返回且仅返回一个 JSON 对象，形如：
{
  "cases": [
    {
      "case_type": "positive | boundary | robustness | security",
      "name": "用例名称，如 [正向] POST /api/login 正常登录",
      "description": "简短说明",
      "request_template": {
        "params": {},
        "url_params": {},
        "headers": {}
      },
      "expected_template": {
        "status_code": 200,
        "description": "期望结果说明：请在此包含对返回包体 (Response Body) 的断言要求（如必须包含 token 字段）"
      }
    }
  ]
}

## 规则

1. **业务真实性**：正向用例必须使用符合业务语义的真实数据（如符合正则的对象 ID、手机号、枚举值等）。
2. **安全测试差异化**：
    - **无鉴权**：`headers` 中必须不包含 `Authorization` 或为空。
    - **错鉴权**：`headers` 中必须包含无效的 `Authorization`（如 `Bearer INVALID`）。
    - **注意**：登录接口通常不需要 Authorization，请根据接口用途智能判断。
3. **断言丰富化**：在 `expected_template.description` 中，明确要求对 Response Body 的关键字段进行校验。
4. **覆盖度**：一次性生成 6 条以上用例，覆盖正向、边界、健壮和安全场景。
5. **参数模板（必填，执行时直接使用）**：
    - `params`：请求体（POST/PUT 等 Body），必须填满接口定义中的必填字段，每个用例根据 case_type 填不同的值。
    - `url_params`：Query 参数。
    - `headers`：必须包含 Content-Type（有 body 时）、以及该用例特有的认证信息。
6. **禁止空 params**：POST/PUT/PATCH 接口的 params 不得为空对象，必须包含与接口定义一致的字段及具体值。每个用例的 params/headers 不同，用于验证不同请求的不同响应。

只输出 JSON，不要 markdown 代码块包裹。"""


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

    user_prompt = USER_PROMPT_TEMPLATE.format(
        case_types=case_types_str,
        path=path,
        method=method,
        summary=summary or "(无)",
        description=description or "(无)",
        parameters=parameters_str,
        request_body=request_body_str,
        headers=headers_str,
    )

    try:
        result = await ai_client.chat(SYSTEM_PROMPT, user_prompt)
        # 写日志文件
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n=== {datetime.now()} ===\n")
            f.write(f"PROMPT:\n{user_prompt}\n")
            f.write(f"RESULT:\n{json.dumps(result, ensure_ascii=False)}\n")
            
        print(f"DEBUG: AI case generator response: {json.dumps(result, ensure_ascii=False)[:200]}...")
    except Exception as e:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n=== {datetime.now()} [ERROR] ===\n")
            f.write(f"PROMPT:\n{user_prompt}\n")
            f.write(f"EXCEPTION:\n{str(e)}\n")
        print(f"DEBUG: AI case generator exception: {e}")
        raise RuntimeError(f"大模型调用失败: {e}") from e
        raise RuntimeError(f"大模型调用失败: {e}") from e

    if not isinstance(result, dict):
        raise ValueError("大模型返回非 JSON 对象")

    raw_cases = result.get("cases")
    if not isinstance(raw_cases, list):
        return []

    out: List[Dict[str, Any]] = []
    for c in raw_cases:
        if not isinstance(c, dict):
            continue
        case_type = (c.get("case_type") or "positive").lower()
        if case_type not in include_types:
            continue
        name = c.get("name") or f"[{case_type}] {method} {path}"
        description = c.get("description") or ""
        req_tpl = c.get("request_template")
        exp_tpl = c.get("expected_template")
        if not isinstance(req_tpl, dict):
            req_tpl = {"params": {}, "url_params": {}, "headers": {}}
        if not isinstance(exp_tpl, dict):
            exp_tpl = {"status_code": 200, "description": ""}
        # 补齐字段，便于执行层使用
        if "params" not in req_tpl:
            req_tpl["params"] = {}
        if "url_params" not in req_tpl:
            req_tpl["url_params"] = {}
        if "headers" not in req_tpl:
            req_tpl["headers"] = {}
        if method in ("POST", "PUT", "PATCH") and req_tpl.get("params") and "Content-Type" not in {
            k.lower() for k in (req_tpl.get("headers") or {}).keys()
        }:
            (req_tpl.setdefault("headers", {}))["Content-Type"] = "application/json"
        out.append({
            "case_type": case_type,
            "name": name,
            "description": description,
            "request_template": req_tpl,
            "expected_template": exp_tpl,
            "source": "ai",
        })
    return out
