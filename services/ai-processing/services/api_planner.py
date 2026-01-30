"""
API Planner - 基于已导入的 Swagger / OpenAPI，生成接口测试计划

当前版本目标：
- 从 SQLite 中的 apis 表读取接口定义
- 为每个接口生成多种用例类型的「计划骨架」：
  - positive: 正向用例
  - boundary: 边界用例（基于 minimum/maximum/minLength/maxLength）
  - robustness: 健壮性/负向用例（缺参数、类型错误等）
  - security: 安全用例（无鉴权 / 错误鉴权）

后续可以在此基础上接入 DataGenerator / AssertionGenerator 做更智能的数据和断言。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import json
import sqlite3


class CaseType(str, Enum):
    """接口用例类型枚举"""

    POSITIVE = "positive"
    BOUNDARY = "boundary"
    ROBUSTNESS = "robustness"
    SECURITY = "security"


DEFAULT_CASE_TYPES: Sequence[CaseType] = (
    CaseType.POSITIVE,
    CaseType.BOUNDARY,
    CaseType.ROBUSTNESS,
    CaseType.SECURITY,
)


@dataclass
class ApiEndpoint:
    """从 apis 表抽象出的简化接口模型"""

    id: int
    path: str
    method: str
    summary: str
    description: str
    base_url: str
    parameters: List[Dict[str, Any]]
    request_body: Dict[str, Any]
    headers: Dict[str, Any]


@dataclass
class ApiTestCase:
    """单个接口用例计划条目（尚未绑定到执行引擎的具体脚本）"""

    endpoint_id: int
    path: str
    method: str
    case_type: CaseType
    name: str
    description: str
    # 请求/断言模板，后续可以由 DataGenerator / AssertionGenerator 进一步填充
    request_template: Dict[str, Any]
    expected_template: Dict[str, Any]


class ApiPlanner:
    """基于 apis 表的规则化 API 测试计划生成器"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ====== 对外主入口 ======

    def generate_plan(
        self,
        project_id: str = "default-project",
        include_case_types: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成指定项目下所有接口的测试计划骨架。

        返回结构示例：
        {
            "project_id": "...",
            "generated_at": "...",
            "endpoints": [
                {
                    "id": 1,
                    "path": "/api/login",
                    "method": "POST",
                    "summary": "...",
                    "description": "...",
                    "case_types": ["positive", "boundary", "robustness", "security"],
                    "cases": [ {ApiTestCase ...}, ... ]
                },
                ...
            ]
        }
        """
        endpoints = self._load_endpoints(project_id)

        enabled_types: List[CaseType]
        if include_case_types:
            enabled_types = [
                ct
                for ct in DEFAULT_CASE_TYPES
                if ct.value in {t.lower() for t in include_case_types}
            ]
        else:
            enabled_types = list(DEFAULT_CASE_TYPES)

        endpoint_items: List[Dict[str, Any]] = []
        for ep in endpoints:
            cases = self._generate_cases_for_endpoint(ep, enabled_types)
            endpoint_items.append(
                {
                    "id": ep.id,
                    "path": ep.path,
                    "method": ep.method,
                    "summary": ep.summary,
                    "description": ep.description,
                    "base_url": ep.base_url,
                    "case_types": [ct.value for ct in enabled_types],
                    "cases": [asdict(c) for c in cases],
                }
            )

        return {
            "project_id": project_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "endpoint_count": len(endpoints),
            "endpoints": endpoint_items,
        }

    # ====== 内部实现：加载接口定义 ======

    def _load_endpoints(self, project_id: str) -> List[ApiEndpoint]:
        """从 apis 表加载指定项目的接口定义"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, path, method, summary, description, base_url, parameters, request_body, headers
            FROM apis
            WHERE project_id = ?
            ORDER BY path, method
            """,
            (project_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        endpoints: List[ApiEndpoint] = []
        for row in rows:
            try:
                parameters = json.loads(row["parameters"] or "[]")
            except Exception:
                parameters = []
            try:
                request_body = json.loads(row["request_body"] or "{}")
            except Exception:
                request_body = {}
            try:
                headers = json.loads(row["headers"] or "{}")
            except Exception:
                headers = {}

            endpoints.append(
                ApiEndpoint(
                    id=row["id"],
                    path=row["path"],
                    method=(row["method"] or "GET").upper(),
                    summary=row["summary"] or "",
                    description=row["description"] or "",
                    base_url=row["base_url"] or "",
                    parameters=parameters if isinstance(parameters, list) else [],
                    request_body=request_body if isinstance(request_body, dict) else {},
                    headers=headers if isinstance(headers, dict) else {},
                )
            )

        return endpoints

    # ====== 内部实现：按接口生成用例骨架 ======

    def _generate_cases_for_endpoint(
        self,
        ep: ApiEndpoint,
        case_types: Sequence[CaseType],
    ) -> List[ApiTestCase]:
        # 无 schema/参数 时无法生成有差异的真实用例，不生成假用例
        if not self._has_meaningful_schema(ep):
            return []

        cases: List[ApiTestCase] = []

        if CaseType.POSITIVE in case_types:
            cases.append(self._make_positive_case(ep))

        if CaseType.BOUNDARY in case_types:
            cases.extend(self._make_boundary_cases(ep))

        if CaseType.ROBUSTNESS in case_types:
            cases.extend(self._make_robustness_cases(ep))

        if CaseType.SECURITY in case_types and self._looks_secure_endpoint(ep):
            cases.extend(self._make_security_cases(ep))

        return cases

    # ====== 各类用例构造 ======

    def _make_positive_case(self, ep: ApiEndpoint) -> ApiTestCase:
        """正向用例：所有必填参数给出典型合法值"""
        params = self._build_sample_params(ep, mode="valid")
        url_params = self._build_sample_query(ep, mode="valid")
        req = {
            "params": params,
            "url_params": url_params,
            "headers": self._default_headers_for_endpoint(ep, has_body=bool(params)),
        }
        expected = {
            "status_code": 200,
            "description": "接口应按文档描述正常返回，业务成功",
        }
        name = f"[正向] {ep.method} {ep.path}"
        desc = ep.summary or ep.description or "接口正向功能验证"
        return ApiTestCase(
            endpoint_id=ep.id,
            path=ep.path,
            method=ep.method,
            case_type=CaseType.POSITIVE,
            name=name,
            description=desc,
            request_template=req,
            expected_template=expected,
        )

    def _make_boundary_cases(self, ep: ApiEndpoint) -> List[ApiTestCase]:
        """边界用例：基于 numeric / string 约束生成真实差异的边界场景（含 body 属性）"""
        cases: List[ApiTestCase] = []
        # path/query 参数
        param_defs = list(self._iter_params(ep))
        # body 属性（从 request_body schema）
        body_props = self._iter_body_properties(ep)
        all_defs = param_defs + body_props

        for p in all_defs:
            schema = p.get("schema", {})
            p_type = schema.get("type", "string")
            name = p.get("name", "")
            if not name:
                continue

            boundary_values = self._build_boundary_values(schema)
            if not boundary_values:
                continue

            for label, value in boundary_values.items():
                base_params = self._build_sample_params(ep, mode="valid")
                base_query = self._build_sample_query(ep, mode="valid")
                req = {
                    "params": dict(base_params),
                    "url_params": dict(base_query),
                    "headers": self._default_headers_for_endpoint(ep, has_body=bool(base_params or base_query)),
                }
                if p.get("in") == "query":
                    target = req["url_params"]
                else:
                    target = req["params"]
                target[name] = value
                expected = {
                    "status_code": 200,
                    "description": f"验证参数 {name} 在边界场景 {label} 下接口行为是否符合预期",
                }
                case_name = f"[边界-{label}] {ep.method} {ep.path}::{name}"
                desc = f"参数 {name} ({p_type}) 在 {label} 边界值下的行为验证。"
                cases.append(
                    ApiTestCase(
                        endpoint_id=ep.id,
                        path=ep.path,
                        method=ep.method,
                        case_type=CaseType.BOUNDARY,
                        name=case_name,
                        description=desc,
                        request_template=req,
                        expected_template=expected,
                    )
                )

        return cases

    def _make_robustness_cases(self, ep: ApiEndpoint) -> List[ApiTestCase]:
        """健壮性/负向用例：缺必填参数、类型错误等（含 path/query 与 body 属性）"""
        cases: List[ApiTestCase] = []
        # path/query 必填 + body 必填
        required_params = [p for p in self._iter_params(ep) if p.get("required")]
        required_body = [p for p in self._iter_body_properties(ep) if p.get("required")]
        all_required = required_params + required_body

        base_valid_params = self._build_sample_params(ep, mode="valid")
        base_valid_query = self._build_sample_query(ep, mode="valid")

        # 缺少每一个必填参数（含 body 属性）
        for p in all_required:
            name = p.get("name", "")
            if not name:
                continue
            req_params = dict(base_valid_params)
            req_query = dict(base_valid_query)

            if p.get("in") == "query":
                req_query.pop(name, None)
            else:
                req_params.pop(name, None)

            req = {
                "params": req_params,
                "url_params": req_query,
                "headers": self._default_headers_for_endpoint(ep, has_body=bool(req_params)),
            }
            expected = {
                "status_code": 400,
                "description": f"缺少必填参数 {name} 时，接口应返回参数错误",
            }
            case_name = f"[健壮-缺参] {ep.method} {ep.path}::{name}"
            desc = f"验证缺少必填参数 {name} 时的容错与错误提示。"
            cases.append(
                ApiTestCase(
                    endpoint_id=ep.id,
                    path=ep.path,
                    method=ep.method,
                    case_type=CaseType.ROBUSTNESS,
                    name=case_name,
                    description=desc,
                    request_template=req,
                    expected_template=expected,
                )
            )

        # 类型错误：数字型参数/属性改成字符串（path/query + body）
        for p in list(self._iter_params(ep)) + self._iter_body_properties(ep):
            schema = p.get("schema", {})
            if schema.get("type") not in ("integer", "number"):
                continue
            name = p.get("name", "")
            if not name:
                continue
            req_params = dict(self._build_sample_params(ep, mode="valid"))
            req_query = dict(self._build_sample_query(ep, mode="valid"))
            target = req_query if p.get("in") == "query" else req_params
            target[name] = "INVALID_NUMBER"
            req = {
                "params": req_params,
                "url_params": req_query,
                "headers": self._default_headers_for_endpoint(ep, has_body=bool(req_params)),
            }
            expected = {
                "status_code": 400,
                "description": f"参数 {name} 类型错误时应被后端校验拦截",
            }
            case_name = f"[健壮-类型错] {ep.method} {ep.path}::{name}"
            desc = f"验证数值参数 {name} 传入非法字符串时的健壮性。"
            cases.append(
                ApiTestCase(
                    endpoint_id=ep.id,
                    path=ep.path,
                    method=ep.method,
                    case_type=CaseType.ROBUSTNESS,
                    name=case_name,
                    description=desc,
                    request_template=req,
                    expected_template=expected,
                )
            )

        return cases

    def _make_security_cases(self, ep: ApiEndpoint) -> List[ApiTestCase]:
        """安全用例：无鉴权 / 错误鉴权（请求头真实差异：无 Authorization vs 错误 Token）"""
        cases: List[ApiTestCase] = []

        params = self._build_sample_params(ep, mode="valid")
        url_params = self._build_sample_query(ep, mode="valid")
        has_body = bool(params)

        # 无鉴权：明确不包含 Authorization
        h_no_auth = self._default_headers_for_endpoint(ep, has_body=has_body)
        for k in list(h_no_auth.keys()):
            if k.lower() in ("authorization", "auth", "token", "bearer"):
                del h_no_auth[k]
        req_no_auth = {
            "params": params,
            "url_params": url_params,
            "headers": h_no_auth,
        }
        expected_no_auth = {
            "status_code": 401,
            "description": "未携带鉴权信息时，应被拒绝访问。",
        }
        cases.append(
            ApiTestCase(
                endpoint_id=ep.id,
                path=ep.path,
                method=ep.method,
                case_type=CaseType.SECURITY,
                name=f"[安全-无鉴权] {ep.method} {ep.path}",
                description="验证未携带 Authorization 等鉴权信息时的安全控制。",
                request_template=req_no_auth,
                expected_template=expected_no_auth,
            )
        )

        # 错误鉴权：携带错误 Token
        h_bad = self._default_headers_for_endpoint(ep, has_body=has_body)
        h_bad["Authorization"] = "Bearer INVALID_TOKEN"
        req_bad_auth = {
            "params": params,
            "url_params": url_params,
            "headers": h_bad,
        }
        expected_bad_auth = {
            "status_code": 401,
            "description": "携带错误 Token 时，应被拒绝访问。",
        }
        cases.append(
            ApiTestCase(
                endpoint_id=ep.id,
                path=ep.path,
                method=ep.method,
                case_type=CaseType.SECURITY,
                name=f"[安全-错鉴权] {ep.method} {ep.path}",
                description="验证携带错误/过期的 Token 时的安全控制。",
                request_template=req_bad_auth,
                expected_template=expected_bad_auth,
            )
        )

        return cases

    # ====== 工具方法：参数遍历与示例值构造 ======

    def _has_meaningful_schema(self, ep: ApiEndpoint) -> bool:
        """是否有可生成差异化用例的 schema（parameters 或 request_body 含 properties）"""
        if self._iter_params(ep):
            return True
        schema = self._get_body_schema(ep)
        if not schema:
            return False
        props = schema.get("properties") or schema.get("Properties") or {}
        if isinstance(props, dict) and props:
            return True
        # 扁平 body 如 { "phone": "", "code": "" }
        if isinstance(schema, dict):
            for k in ("type", "properties", "required", "content", "schema", "description"):
                if k in schema and isinstance(schema.get(k), (dict, list)):
                    return True
            for k, v in schema.items():
                if k in ("type", "properties", "required", "content", "schema", "description"):
                    continue
                if isinstance(v, (str, int, float, bool)) or v is None or (isinstance(v, dict) and (v.get("type") or v.get("properties"))):
                    return True
        return False

    def _iter_body_properties(self, ep: ApiEndpoint) -> List[Dict[str, Any]]:
        """从 request_body schema 得到 body 属性列表，每项 { name, schema, required }"""
        schema = self._get_body_schema(ep)
        if not schema:
            return []
        props = schema.get("properties") or schema.get("Properties") or {}
        required_set = set(schema.get("required") or schema.get("Required") or [])
        if not isinstance(props, dict):
            return []
        out: List[Dict[str, Any]] = []
        for name, prop_schema in props.items():
            if not isinstance(prop_schema, dict):
                continue
            out.append({
                "name": name,
                "schema": prop_schema,
                "required": name in required_set,
                "in": "body",
            })
        # 兼容扁平 body：schema 为 { "phone": "", "code": "" }
        if not out and isinstance(schema, dict):
            for k, v in schema.items():
                if k in ("type", "properties", "required", "content", "schema", "description"):
                    continue
                if isinstance(v, dict) and (v.get("type") or v.get("properties")):
                    out.append({"name": k, "schema": v, "required": False, "in": "body"})
                elif isinstance(v, (str, int, float, bool)) or v is None:
                    out.append({"name": k, "schema": {"type": "string"}, "required": False, "in": "body"})
        return out

    def _get_body_schema(self, ep: ApiEndpoint) -> Optional[Dict[str, Any]]:
        """从 OpenAPI request_body 中提取 JSON Schema（用于生成 Body 示例）"""
        rb = ep.request_body or {}
        if not isinstance(rb, dict):
            return None
        # OpenAPI 3: requestBody.content["application/json"].schema
        content = rb.get("content") or rb.get("Content") or {}
        if isinstance(content, dict):
            json_media = content.get("application/json") or content.get("application/json; charset=utf-8") or {}
            if isinstance(json_media, dict) and json_media.get("schema"):
                return json_media["schema"]
        # 兼容：request_body 直接就是 schema（type: object, properties: ...）
        if rb.get("type") == "object" or rb.get("properties"):
            return rb
        # 兼容：扁平键值对，如 { "phone": "", "code": "" }（无 content 时当作 body 模板）
        if rb and "content" not in rb and "schema" not in rb:
            return rb
        return None

    def _build_sample_body(self, ep: ApiEndpoint, mode: str = "valid") -> Dict[str, Any]:
        """从 request_body 的 schema 构造 Body 示例值（POST/PUT 等请求体）"""
        schema = self._get_body_schema(ep)
        if not schema:
            return {}
        props = schema.get("properties") or schema.get("Properties") or {}
        if not isinstance(props, dict):
            return {}
        out: Dict[str, Any] = {}
        for name, prop_schema in props.items():
            if not isinstance(prop_schema, dict):
                continue
            out[name] = self._sample_value_for_schema(prop_schema, mode=mode)
        if not out and isinstance(schema, dict):
            # 兼容：schema 为 { "phone": "", "code": "" } 等扁平结构
            for k, v in schema.items():
                if k in ("type", "properties", "required", "content", "schema", "description"):
                    continue
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v if v != "" else "x"
                elif isinstance(v, dict) and (v.get("type") or v.get("properties")):
                    out[k] = self._sample_value_for_schema(v, mode=mode)
        return out

    def _iter_params(self, ep: ApiEndpoint) -> List[Dict[str, Any]]:
        """统一遍历 path/query/header 级参数（不含 body schema）"""
        return ep.parameters or []

    def _build_sample_params(self, ep: ApiEndpoint, mode: str = "valid") -> Dict[str, Any]:
        """构造 body/表单参数的简单示例值。优先使用 request_body 的 schema，否则用 parameters 中 in!=query 的"""
        body_from_schema = self._build_sample_body(ep, mode=mode)
        if body_from_schema:
            return body_from_schema
        params: Dict[str, Any] = {}
        for p in self._iter_params(ep):
            if p.get("in") == "query":
                continue
            name = p.get("name", "")
            schema = p.get("schema", {})
            params[name] = self._sample_value_for_schema(schema, mode=mode)
        return params

    def _default_headers_for_endpoint(self, ep: ApiEndpoint, has_body: bool = False) -> Dict[str, str]:
        """合并接口定义的 headers，并在有 Body 时默认加 Content-Type"""
        h: Dict[str, str] = {}
        if ep.headers and isinstance(ep.headers, dict):
            for k, v in ep.headers.items():
                if v is not None:
                    h[str(k)] = str(v)
        if has_body and "content-type" not in (k.lower() for k in h.keys()):
            h["Content-Type"] = "application/json"
        return h

    def _build_sample_query(self, ep: ApiEndpoint, mode: str = "valid") -> Dict[str, Any]:
        """构造 query 参数的简单示例值"""
        params: Dict[str, Any] = {}
        for p in self._iter_params(ep):
            if p.get("in") != "query":
                continue
            name = p.get("name", "")
            schema = p.get("schema", {})
            params[name] = self._sample_value_for_schema(schema, mode=mode)
        return params

    def _sample_value_for_schema(self, schema: Dict[str, Any], mode: str = "valid") -> Any:
        """根据简单的 schema 信息构造示例值（后续可由 DataGenerator 替代）"""
        t = schema.get("type", "string")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")

        if t in ("integer", "number"):
            base = minimum if isinstance(minimum, (int, float)) else 1
            if mode == "valid":
                if isinstance(maximum, (int, float)) and maximum >= base:
                    return int((base + maximum) / 2)
                return int(base)
            return int(base)

        if t == "boolean":
            return True

        # string
        length = 5
        if isinstance(min_length, int):
            length = max(length, min_length)
        if isinstance(max_length, int):
            length = min(length, max_length)
        return "x" * max(length, 1)

    def _build_boundary_values(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """根据 schema 生成一组简单边界值标签 -> 值"""
        t = schema.get("type", "string")
        values: Dict[str, Any] = {}

        if t in ("integer", "number"):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if isinstance(minimum, (int, float)):
                values["min"] = minimum
                values["min-1"] = minimum - 1
            if isinstance(maximum, (int, float)):
                values["max"] = maximum
                values["max+1"] = maximum + 1
        elif t == "string":
            min_len = schema.get("minLength")
            max_len = schema.get("maxLength")
            if isinstance(min_len, int):
                values["minLength"] = "x" * min_len
                if min_len > 0:
                    values["minLength-1"] = "x" * (min_len - 1)
            if isinstance(max_len, int) and max_len > 0:
                values["maxLength"] = "x" * max_len
                values["maxLength+1"] = "x" * (max_len + 1)

        return values

    def _looks_secure_endpoint(self, ep: ApiEndpoint) -> bool:
        """
        粗略判断该接口是否需要安全用例：
        - 路径中包含敏感关键词
        - 或者已有 Authorization 相关的 header 定义（未来可以从 headers 列增强）
        """
        path_lower = (ep.path or "").lower()
        sensitive_keywords = [
            "login",
            "logout",
            "token",
            "auth",
            "user",
            "account",
            "password",
        ]
        if any(k in path_lower for k in sensitive_keywords):
            return True
        # 保守起见，如果方法是非 GET，也可以考虑生成一部分安全用例
        return ep.method.upper() != "GET"

