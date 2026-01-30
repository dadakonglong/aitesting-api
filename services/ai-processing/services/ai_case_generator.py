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
from typing import Any, Dict, List, Optional


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
        "description": "期望结果说明"
      }
    }
  ]
}

## 规则
1. **params**：请求体（POST/PUT 等 Body），对象；GET 无 body 则 {}。
2. **url_params**：Query 参数，对象；无则 {}。
3. **headers**：必须包含 Content-Type: application/json（当有 body 时）；鉴权类接口可含 Authorization。
4. **正向用例**：使用符合业务语义的真实数据（如真实格式手机号、合理长度字符串、合理数字），预期 200/201。
5. **边界用例**：必须与“边界”相关：空字符串、最大/最小长度、0、负数、最大整数、超长字符串、特殊字符等，并说明预期（200 或 4xx）。
6. **健壮用例**：必须与“异常/健壮”相关：缺必填参数、类型错误（如数字字段传字符串）、非法枚举、格式错误等，预期 400/422。
7. **安全用例**：无 Authorization、或 Bearer 错误/过期 token，预期 401/403。
8. 每个用例的 request_template 必须与 case_type 和 name 一致，不要生成“名字是边界但请求与正向完全一样”的用例。
9. 只输出 JSON，不要 markdown 代码块包裹。"""


USER_PROMPT_TEMPLATE = """请为以下接口生成测试用例，需包含类型：{case_types}。

## 接口定义
- 路径: {path}
- 方法: {method}
- 摘要: {summary}
- 描述: {description}
- 参数(OpenAPI parameters): {parameters}
- 请求体(OpenAPI requestBody): {request_body}

请为每种请求类型生成至少 1 条**真实**用例（请求体/参数要与类型匹配），直接返回上述格式的 JSON。"""


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

    user_prompt = USER_PROMPT_TEMPLATE.format(
        case_types=case_types_str,
        path=path,
        method=method,
        summary=summary or "(无)",
        description=description or "(无)",
        parameters=parameters_str,
        request_body=request_body_str,
    )

    try:
        result = await ai_client.chat(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
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
