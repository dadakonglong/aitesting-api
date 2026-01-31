"""
单接口 AI 测试流水线 - 五阶段，每阶段调用大模型 Agent

1. 需求理解：RAG 检索 Agent（从知识库检索 + 大模型结构化理解）
2. 测试计划：Planner Agent（大模型分析 API 文档并制定测试计划）
3. 代码生成：Generator Agent（大模型生成 pytest + requests 测试代码）
4. 测试执行：Executor Agent（大模型指导执行策略，后端执行用例）
5. 结果分析：Analyzer Agent（大模型分析结果并生成报告）
"""

from __future__ import annotations

import json
import re
import math
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# 保证日志文件写在当前文件同级目录 (services/ai-processing/services/...)
# 注意：single_api_pipeline.py 在 services/ai-processing/services/ 下
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_debug.log")

def _log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        pass

from .api_planner import ApiPlanner
from .ai_case_generator import generate_cases_for_endpoint as ai_generate_cases


# ============= Agent 系统提示词（用户提供） =============

RAG_RETRIEVAL_SYSTEM_PROMPT = """你是接口分析专家。你的任务是对「当前目标接口」做结构化分析。

## 分析范围

- **只分析当前目标接口**：根据用户描述确定一个目标接口，对该接口做详细分析（实体、关系、文本块、请求参数、请求体、响应、认证等）。
- **相关接口**：检索到的其他接口可以列出（作为相关接口），但不需要对它们做分析。

## 输出格式

请以 JSON 格式返回，包含：
- entities：实体列表（每项含 entity_name, entity_type, description），仅针对当前目标接口。
- relationships：关系列表。
- chunks：文本块列表（每项含 content），仅针对当前目标接口的请求参数、请求体、响应格式、认证方式等。"""

PLANNER_SYSTEM_PROMPT = """你是测试计划专家。你的任务是为「当前接口」制定测试计划。

## 范围

- 仅针对当前目标接口制定计划，不包含其他接口的测试内容。

## 测试类型

- **功能测试**：验证该接口功能正确性
- **安全测试**：验证认证、授权、输入验证
- **边界测试**：验证边界条件和异常情况
- **健壮性测试**：缺参、类型错误、格式错误等

## 输出格式

生成 Markdown 格式的测试计划，包含：测试目标与范围（仅当前接口）、测试用例列表、测试数据与环境要求、预期结果与验收标准。

请以 JSON 格式返回：{"markdown": "完整 Markdown 字符串"}。"""

GENERATOR_SYSTEM_PROMPT = """你是 pytest 测试代码生成专家。
你的任务是根据测试计划生成高质量的 pytest 测试脚本。

## 代码规范

- 使用 pytest + requests 框架
- 集成 Allure 报告装饰器
- 支持参数化测试
- 包含详细的步骤和断言

## 文件结构

生成以下文件：
- test_*.py：测试文件
- conftest.py：pytest 配置和 fixtures
- pytest.ini：pytest 配置文件

请以 JSON 格式返回：{"code": "test_*.py 的完整代码", "conftest": "conftest.py 内容（可选）", "pytest_ini": "pytest.ini 内容（可选）"}。至少包含 code。不要用 markdown 代码块包裹。"""

# Playwright 接口测试代码生成：Generator Agent 解析测试计划 + 用例列表，输出 Playwright 文件
GENERATOR_PLAYWRIGHT_SYSTEM_PROMPT = """你是 Playwright 接口测试代码生成专家。你的任务是根据「测试计划」和「接口用例列表」生成可直接运行的 Playwright 接口测试文件。

## 代码生成的质量要求（非常重要）

1. **严格区分 Headers**：如果用例列表中包含了 `headers`（尤其是安全测试中的 Authorization），**必须**在 `request` 调用中显式配置它们。不要忽略 headers 差异。
2. **增强断言逻辑**：不要只检查 `status().toBe(200)`。
    - **正向用例**：必须先解析 JSON (`const body = await response.json()`)，然后检查关键业务字段（如 `expect(body).toHaveProperty('token')`）。
    - **异常用例**：检查返回的错误消息 `message` 或 `code`。
3. **理解业务逻辑**：登录接口通常不需要 Authorization，资源操作通常需要。
4. **代码风格**：使用 TypeScript，代码整洁。

## 输出格式（必须严格遵循）

- 仅输出一个完整的 TypeScript 测试文件代码。
- 必须包含：import { test, expect } from '@playwright/test';
- 使用 test.describe() 包裹。
- 每个用例对应一个 test()。
- 不要解释，直接输出代码。"""

EXECUTOR_SYSTEM_PROMPT = """你是测试执行专家。
你的任务是执行 pytest 测试并收集结果。

## 执行策略

- 支持 pytest-xdist 并行执行
- 自动生成 Allure JSON 结果
- 可生成 Allure HTML 报告
- 支持失败重试

## 结果收集

收集以下信息：
- 测试通过/失败/跳过数量
- 执行时间和性能数据
- 失败用例的详细日志
- Allure 报告路径

当前由后端执行 HTTP 用例（非本地 pytest），请根据测试计划与用例列表，输出 JSON：{"execution_summary": "执行策略简要说明", "cases_to_run": "将执行的用例数量或说明"}。"""

ANALYZER_SYSTEM_PROMPT = """你是测试结果分析专家。
你的任务是分析测试结果并提供洞察。

## 分析内容

- 执行概览和统计
- 失败用例分析
- 根因识别
- 改进建议

## 报告格式

生成 Markdown 格式的分析报告，包含：
- 测试摘要
- 可视化图表（通过 Chart MCP）
- 失败分析
- 优化建议

请以 JSON 格式返回：{"report": "完整 Markdown 报告字符串"}。"""


# ---------- 知识库检索（RAG 数据源，6 种模式） ----------

# 检索模式：local=本地实体关系, global=全局探索, hybrid=混合, naive=向量相似, mix=综合(推荐), bypass=直接查询
RAG_MODES = ("local", "global", "hybrid", "naive", "mix", "bypass")


def _load_apis_from_db(db_path: str, project_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """从 apis 表加载项目下所有接口，返回统一结构的列表。"""
    conn = sqlite3.connect(db_path)
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
    apis = []
    for row in rows:
        apis.append({
            "id": row["id"],
            "path": row["path"],
            "method": row["method"],
            "summary": row["summary"] or "",
            "description": row["description"] or "",
            "base_url": row["base_url"] or "",
            "parameters": json.loads(row["parameters"] or "[]"),
            "request_body": json.loads(row["request_body"] or "{}"),
            "headers": json.loads(row["headers"] or "{}"),
        })
    if limit is not None:
        apis = apis[:limit]
    return apis


def _extract_keywords(query: str) -> List[str]:
    """从用户描述中提取可能的关键词（仅完整词）。"""
    stop = {"为", "生成", "完整", "测试", "接口", "的", "一个", "做", "写", "请", "帮我"}
    words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", query)
    return [w for w in words if len(w) >= 2 and w not in stop]


def _extract_keywords_enhanced(query: str) -> List[str]:
    """
    增强关键词：除完整词外，对中文等长词做 2 字切分，便于「手机登录」匹配「手机号登录」等。
    返回去重后的关键词列表。
    """
    stop = {"为", "生成", "完整", "测试", "接口", "的", "一个", "做", "写", "请", "帮我"}
    words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", query)
    seen: set = set()
    result: List[str] = []
    for w in words:
        if len(w) < 2 or w in stop:
            continue
        if w not in seen:
            seen.add(w)
            result.append(w)
        # 中文/字母数字长词：增加 2 字（或 2 字符）子串，提高召回
        if len(w) >= 3:
            for i in range(len(w) - 1):
                sub = w[i : i + 2]
                if sub not in seen and (sub not in stop):
                    seen.add(sub)
                    result.append(sub)
    return result


def _score_api_row(row: Dict[str, Any], keywords: List[str], text: str) -> int:
    """计算单条 API 与关键词的匹配得分。"""
    return sum(1 for k in keywords if k in text)


def rag_query_data(
    db_path: str,
    project_id: str,
    query: str,
    limit: int = 10,
    mode: str = "mix",
) -> List[Dict[str, Any]]:
    """
    从知识库（apis 表）按指定模式检索与用户描述相关的接口。

    支持 6 种模式：
    - local: 本地实体和关系检索（增强关键词 + 严格匹配）
    - global: 全局探索（放宽匹配，返回更多候选）
    - hybrid: 混合检索（增强关键词 + 放宽一次，合并去重）
    - naive: 向量相似性思路（当前用增强关键词 + 任意词匹配）
    - mix: 综合检索（推荐）：hybrid + bypass 补全，按得分排序去重
    - bypass: 直接查询（返回项目下全部接口，便于未命中时仍能选到）
    """
    all_apis = _load_apis_from_db(db_path, project_id, limit=None)
    _log(f"RAG: project_id={project_id}, query={query}, all_apis_count={len(all_apis)}")
    if not all_apis:
        return []

    keywords = _extract_keywords_enhanced(query)
    _log(f"RAG: keywords={keywords}")
    # 用于拼接检索的 API 文本（path/summary/description/method）
    def api_text(api: Dict[str, Any]) -> str:
        return " ".join(
            str(api.get(k) or "") for k in ("path", "summary", "description", "method")
        ).lower()

    def score_and_tag(apis: List[Dict[str, Any]], use_keywords: List[str]) -> List[Dict[str, Any]]:
        out = []
        for a in apis:
            text = api_text(a)
            score = _score_api_row(a, use_keywords, text) if use_keywords else 1
            r = {**a, "_score": score}
            out.append(r)
        return out

    if mode == "bypass":
        # 直接查询：返回项目下全部接口（截断到 limit）
        for a in all_apis:
            a["_score"] = 1
        return all_apis[: limit or 50]

    if mode == "global":
        # 全局：增强关键词，任意词命中即保留，多返回一些
        use_kw = _extract_keywords_enhanced(query)
        scored = score_and_tag(all_apis, use_kw)
        scored = [x for x in scored if x["_score"] > 0]
        scored.sort(key=lambda x: -x["_score"])
        for a in scored:
            a.pop("_score", None)
        return scored[: limit or 20]

    if mode == "local":
        # 本地实体和关系：增强关键词，仅保留得分 > 0
        use_kw = _extract_keywords_enhanced(query)
        if not use_kw:
            return all_apis[:limit]
        scored = score_and_tag(all_apis, use_kw)
        scored = [x for x in scored if x["_score"] > 0]
        scored.sort(key=lambda x: -x["_score"])
        for a in scored:
            a.pop("_score", None)
        return scored[:limit]

    if mode == "naive":
        # 向量相似性思路：当前用增强关键词 + 放宽（任意一词命中）
        use_kw = _extract_keywords_enhanced(query)
        if not use_kw:
            return all_apis[:limit]
        scored = score_and_tag(all_apis, use_kw)
        scored = [x for x in scored if x["_score"] > 0]
        scored.sort(key=lambda x: -x["_score"])
        for a in scored:
            a.pop("_score", None)
        return scored[:limit]

    if mode == "hybrid":
        # 混合：先 local，若结果过少则用更宽关键词再扫一遍合并
        use_kw = _extract_keywords_enhanced(query)
        scored = score_and_tag(all_apis, use_kw)
        by_id = {a["id"]: a for a in scored}
        high = [x for x in scored if x["_score"] > 0]
        if len(high) < 3 and use_kw:
            # 放宽：任意 1 字子串（仅中文 2 字词）再匹配一次
            for a in scored:
                if a["_score"] == 0:
                    text = api_text(a)
                    if any(k in text for k in use_kw):
                        a["_score"] = 1
                        by_id[a["id"]] = a
            high = [x for x in scored if x["_score"] > 0]
        high.sort(key=lambda x: -x["_score"])
        for a in high:
            a.pop("_score", None)
        return high[:limit]

    # mix（推荐）：综合 = hybrid 结果 + 若不足则用 bypass 补全，去重按得分排序
    use_kw = _extract_keywords_enhanced(query)
    scored = score_and_tag(all_apis, use_kw)
    by_id = {}
    for a in scored:
        by_id[a["id"]] = a
    high = [x for x in scored if x["_score"] > 0]
    if len(high) < 3 and use_kw:
        for a in scored:
            if a["_score"] == 0:
                text = api_text(a)
                if any(k in text for k in use_kw):
                    a["_score"] = 1
                    by_id[a["id"]] = a
        high = [x for x in scored if x["_score"] > 0]
    high.sort(key=lambda x: -x["_score"])
    # 不足 limit 时用未命中的接口按原顺序补足（bypass 补全）
    out_ids = {a["id"] for a in high}
    for a in all_apis:
        if a["id"] not in out_ids:
            high.append({**a, "_score": 0})
    high.sort(key=lambda x: -x.get("_score", 0))
    for a in high:
        a.pop("_score", None)
    return high[:limit]


# ---------- 阶段 1：需求理解（RAG 检索 Agent） ----------


async def requirement_understanding(
    ai_client: Any,
    user_input: str,
    project_id: str,
    db_path: str,
) -> Dict[str, Any]:
    """
    阶段 1（接口分析）：RAG 检索 + 大模型结构化分析，仅分析当前目标接口；相关接口可列出但不分析。
    返回：entities, relationships, chunks, api_candidates, intent
    """
    # 1) 从知识库检索（综合检索 mix 模式，增强关键词 + 补全，便于命中「手机登录」等）
    api_candidates = rag_query_data(db_path, project_id, user_input, limit=10, mode="mix")
    if not api_candidates:
        # 无数据时仍调用大模型做意图理解
        user_prompt = f"用户描述：{user_input}\n\n知识库中未检索到匹配的 API 接口。请根据用户描述推断意图，并返回 JSON：entities（至少一项未识别接口）、relationships、chunks（说明未找到接口）。"
        out = await ai_client.chat(RAG_RETRIEVAL_SYSTEM_PROMPT, user_prompt)
        if isinstance(out, dict) and (out.get("entities") or out.get("chunks")):
            out["api_candidates"] = []
            out["intent"] = out.get("intent") or user_input
            return out
        return {
            "entities": [{"entity_name": "未识别接口", "entity_type": "API_ENDPOINT", "description": user_input}],
            "relationships": [],
            "chunks": [{"content": "未在项目中发现匹配接口，请确认已导入 Swagger 或接口列表。"}],
            "api_candidates": [],
            "intent": user_input,
        }

    # 2) 调用 RAG 检索 Agent：让大模型根据检索结果做结构化理解
    retrieval_context = json.dumps(
        [{"path": a["path"], "method": a["method"], "summary": a.get("summary"), "description": a.get("description"), "parameters": a.get("parameters"), "request_body": a.get("request_body"), "headers": a.get("headers")} for a in api_candidates],
        ensure_ascii=False,
        indent=2,
    )
    user_prompt = f"""用户描述：{user_input}

从知识库检索到的接口列表（第一个为当前目标接口，其余为相关接口）：
{retrieval_context}

请只对「当前目标接口」（用户描述对应的那一个）做详细分析，提取其实体、关系、文本块，返回结构化 JSON：entities、relationships、chunks 均仅针对该接口。相关接口可简要列出，但不要对它们做分析。"""
    out = await ai_client.chat(RAG_RETRIEVAL_SYSTEM_PROMPT, user_prompt)
    if not isinstance(out, dict):
        out = {}
    # 兼容：若模型未返回标准结构，用检索结果拼装
    if not out.get("entities") and api_candidates:
        out["entities"] = [
            {"entity_name": a.get("path") or "API", "entity_type": "API_ENDPOINT", "description": f"{a.get('method')} {a.get('path')} - {a.get('summary') or a.get('description') or '无描述'}"}
            for a in api_candidates[:5]
        ]
    if not out.get("chunks") and api_candidates:
        out["chunks"] = [
            {"content": f"请求参数：{json.dumps(a.get('parameters') or [], ensure_ascii=False)}。请求体：{json.dumps(a.get('request_body') or {}, ensure_ascii=False)}。响应见文档。"}
            for a in api_candidates[:5]
        ]
    out["api_candidates"] = api_candidates
    out["intent"] = out.get("intent") or user_input
    return out


# ---------- 阶段 2：测试计划（Planner Agent） ----------


async def generate_test_plan_md(
    ai_client: Any,
    structured_info: Dict[str, Any],
    api_planner: ApiPlanner,
    project_id: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    阶段 2：调用测试计划 Agent 大模型，根据结构化 API 信息生成 Markdown 测试计划。
    同时用 ApiPlanner + ai_generate_cases 生成可执行用例列表（供阶段 4 执行）。
    """
    api_candidates = structured_info.get("api_candidates") or []
    _log(f"Plan: api_candidates count={len(api_candidates)}")
    entities = structured_info.get("entities") or []
    chunks = structured_info.get("chunks") or []
    intent = structured_info.get("intent") or ""

    if not api_candidates:
        user_prompt = f"用户意图：{intent}\n\n结构化信息：entities={json.dumps(entities, ensure_ascii=False)}，chunks={json.dumps(chunks, ensure_ascii=False)}\n\n请根据以上信息制定测试计划（Markdown），包含测试目标、范围、用例列表、环境要求、验收标准。"
        out = await ai_client.chat(PLANNER_SYSTEM_PROMPT, user_prompt)
        md = (isinstance(out, dict) and out.get("markdown")) or json.dumps(out or {}, ensure_ascii=False, indent=2)
        return md, {"endpoints": [], "markdown": md, "target_api": None}

    # 调用 Planner Agent：仅针对当前目标接口制定测试计划
    context = f"用户意图：{intent}\n\n实体（当前接口）：{json.dumps(entities, ensure_ascii=False)}\n\n文本块/接口细节（当前接口）：{json.dumps(chunks, ensure_ascii=False)}"
    user_prompt = f"""{context}

请仅针对当前目标接口制定测试计划（Markdown），包含：测试目标与范围、功能/安全/边界/健壮性等测试类型、测试用例列表、测试数据与环境要求、预期结果与验收标准。不要包含其他接口的测试内容。"""
    out = await ai_client.chat(PLANNER_SYSTEM_PROMPT, user_prompt)
    plan_md = (isinstance(out, dict) and out.get("markdown")) or ""
    if not plan_md:
        plan_md = json.dumps(out or {}, ensure_ascii=False, indent=2)

    # --- 改进：直接使用 AI 生成高质量用例，不再使用 ApiPlanner 的规则骨架（它会生成前 3 个重复用例） ---
    target_api = api_candidates[0]
    target_path = target_api.get("path")
    target_method = (target_api.get("method") or "GET").upper()
    
    target_ep = {
        "id": target_api.get("id"),
        "path": target_path,
        "method": target_method,
        "summary": target_api.get("summary"),
        "description": target_api.get("description"),
        "base_url": target_api.get("base_url"),
        "parameters": target_api.get("parameters"),
        "request_body": target_api.get("request_body"),
        "headers": target_api.get("headers"),
        "cases": [],
    }
    
    # 强制让 AI 至少生成 6 条覆盖各类场景（正向、边界、健壮、安全）的用例
    needed_types = ["positive", "boundary", "robustness", "security"]
    print(f"DEBUG: Generating AI cases for single API. Types: {needed_types}")
    
    all_ai_cases = await ai_generate_cases(
        ai_client,
        {
            "path": target_ep.get("path") or target_path,
            "method": target_ep.get("method") or target_method,
            "summary": target_ep.get("summary") or target_api.get("summary"),
            "description": target_ep.get("description") or target_api.get("description"),
            "parameters": target_ep.get("parameters") or target_api.get("parameters"),
            "request_body": target_ep.get("request_body") or target_api.get("request_body"),
            "headers": target_ep.get("headers") or target_api.get("headers"),
        },
        include_types=needed_types,
    )
    print(f"DEBUG: AI generated {len(all_ai_cases)} cases")
    target_ep["cases"] = all_ai_cases

    return plan_md, {"endpoints": [target_ep], "markdown": plan_md, "target_api": target_api}


# ---------- 阶段 3：代码生成（Generator Agent） ----------


def _extract_code_from_raw(raw: str) -> str:
    """从原始响应中提取代码：先尝试 JSON 的 code，再尝试 markdown 代码块"""
    if not raw or not isinstance(raw, str):
        return ""
    raw = raw.strip()
    # 0. 尝试 ```json ... ``` 内的 JSON
    json_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if json_block:
        try:
            obj = json.loads(json_block.group(1).strip())
            if isinstance(obj, dict):
                for key in ("code", "content", "test_code", "python_code", "file_content", "result"):
                    v = obj.get(key)
                    if isinstance(v, str) and len(v) > 30:
                        if "```" in v:
                            inner = re.search(r"```(?:python)?\s*([\s\S]*?)```", v)
                            if inner:
                                v = inner.group(1).strip()
                        return v
        except Exception:
            pass
    # 1. 尝试解析整段中的 JSON 取 code
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            obj = json.loads(raw[start:end])
            if isinstance(obj, dict):
                for key in ("code", "content", "test_code", "python_code", "file_content", "result"):
                    v = obj.get(key)
                    if isinstance(v, str) and len(v) > 30:
                        if "```" in v:
                            inner = re.search(r"```(?:python)?\s*([\s\S]*?)```", v)
                            if inner:
                                v = inner.group(1).strip()
                        return v
    except Exception:
        pass
    # 2. 尝试 ```python ... ``` 或 ``` ... ```
    for pattern in (r"```(?:python|py)\s*\n([\s\S]*?)```", r"```\s*\n([\s\S]*?)```"):
        m = re.search(pattern, raw)
        if m:
            code = m.group(1).strip()
            if len(code) > 30 and (
                "def test_" in code or "def " in code or "import pytest" in code or "import requests" in code or "import " in code
            ):
                return code
    # 3. Playwright：```typescript / ```javascript 或含 test.describe / request.post
    for pattern in (
        r"```(?:typescript|ts|javascript|js|typescript|javascript)?\s*([\s\S]*?)```",
        r"```\s*([\s\S]*?)```",
    ):
        m = re.search(pattern, raw)
        if m:
            code = m.group(1).strip()
            if len(code) > 40 and (
                "test.describe" in code or "test(" in code
            ) and ("request." in code or "expect(" in code):
                return code
    # 4. 兜底：如果没用代码块，但看起来像 Playwright 代码
    if "import { test, expect } from" in raw and "test.describe" in raw:
        return raw.strip()
    return ""


def _build_playwright_user_prompt(plan_markdown: str, endpoint: Dict[str, Any]) -> str:
    """根据测试计划与单个 endpoint（含 cases）构建 Playwright 代码生成的 user prompt。用例列表为权威，生成的脚本必须逐条对应。"""
    path = endpoint.get("path") or ""
    method = (endpoint.get("method") or "GET").upper()
    summary = endpoint.get("summary") or endpoint.get("name") or path or "接口"
    cases = endpoint.get("cases") or []
    cases_text = ""
    for i, c in enumerate(cases):
        name = c.get("name") or f"用例{i+1}"
        req = c.get("request_template") or {}
        exp = c.get("expected_template") or {}
        body = req.get("params") or {}   # POST/PUT 请求体
        query = req.get("url_params") or {}  # GET query 或 URL 参数
        headers = req.get("headers") or {} # 包含鉴权等
        status = exp.get("status_code", 200)
        cases_text += f"""
【用例 {i+1}】TC{i+1:03d}: {name}
  - 请求体 data (body): {json.dumps(body, ensure_ascii=False)}
  - URL 参数 params (query): {json.dumps(query, ensure_ascii=False)}
  - 请求头 headers: {json.dumps(headers, ensure_ascii=False)}
  - 预期状态码: {status}
"""
    cases_count = len(cases)
    if not cases_text:
        cases_text = "\n（当前无预生成用例列表，请根据下方测试计划与接口定义自行设计至少 6 条用例：涵盖正向、边界、健壮、安全，并逐条生成对应的 test。）"
        cases_count = 0
    count_instruction = f"本列表共 {cases_count} 条用例，你必须生成恰好 {cases_count} 个 test()，一个不能少、不能多。" if cases_count else "请至少生成 2 个 test()。"
    return f"""## 接口定义（当前接口）
- path: {path}
- method: {method}
- summary: {summary}
- parameters: {json.dumps(endpoint.get("parameters") or [], ensure_ascii=False)}
- request_body: {json.dumps(endpoint.get("request_body") or {}, ensure_ascii=False)}
- headers: {json.dumps(endpoint.get("headers") or {}, ensure_ascii=False)}

## 用例列表（权威输入：必须按此逐条生成，每条对应一个 test，不得遗漏或自行增加）
{cases_text}
{count_instruction}

## 测试计划（背景参考，用于理解测试意图）
{plan_markdown[:4000]}

---
请严格按照「用例列表」生成 Playwright 测试文件：为表中每一条用例生成一个 test('TC001: 用例名', ...)、test('TC002: ...', ...)。{f"共 {cases_count} 个 test()，直至 TC{cases_count:03d}。" if cases_count else ""} 请求体 data、URL 参数 params、预期 expect(response.status()).toBe(xxx) 与表中完全一致。path 使用完整路径 '{path}'。只输出代码或 JSON({{"code": "..."}})。"""


async def generate_playwright_code_from_plan(
    ai_client: Any,
    plan_markdown: str,
    plan_payload: Dict[str, Any],
) -> str:
    """
    阶段 3（Playwright）：直接使用 chat_raw 获取代码，更稳定。
    """
    endpoints = plan_payload.get("endpoints") or []
    endpoint = endpoints[0] if endpoints else {}
    user_prompt = _build_playwright_user_prompt(plan_markdown, endpoint)
    code = ""
    
    try:
        # 直接使用 chat_raw 生成代码文本
        raw = await ai_client.chat_raw(GENERATOR_PLAYWRIGHT_SYSTEM_PROMPT, user_prompt)
        if not raw:
            return ""
        # 尝试提取
        code = _extract_code_from_raw(raw)
        if code:
            return code
        # 如果没匹配到，但看起来像代码，直接返回
        if "import { test, expect }" in raw and "test(" in raw:
            return raw.strip()
    except Exception as e:
        print(f"DEBUG: generate playwright code failed: {e}")
    
    if not code or len(code) < 50:
        # 兜底：至少给出 Playwright 骨架，便于用户在此基础上修改
        path = endpoint.get("path") or "/api/example"
        method = (endpoint.get("method") or "POST").upper()
        summary = endpoint.get("summary") or "接口"
        code = f"""import {{ test, expect }} from '@playwright/test';

test.describe('{summary}测试', () => {{
  test('TC001: 正向请求', async ({{ request }}) => {{
    const response = await request.{method.lower()}('{path}', {{
      data: {{ }}
    }});
    expect(response.status()).toBeLessThan(400);
  }});
}});
"""
    return code


async def generate_test_code(
    ai_client: Any,
    plan_markdown: str,
    api_info: Dict[str, Any],
) -> str:
    """
    阶段 3：调用测试生成 Agent 大模型，根据测试计划与接口定义生成 pytest + requests 测试代码。
    返回 test_*.py 的完整代码字符串（主文件）；conftest/pytest.ini 可选。
    """
    path = api_info.get("path") or ""
    method = (api_info.get("method") or "GET").upper()
    parameters = api_info.get("parameters")
    if not isinstance(parameters, (list, dict)):
        parameters = []
    request_body = api_info.get("request_body")
    if not isinstance(request_body, dict):
        request_body = {}

    user_prompt = f"""## 测试计划
{plan_markdown[:4000]}

## 接口定义
- path: {path}
- method: {method}
- parameters: {json.dumps(parameters, ensure_ascii=False)}
- request_body: {json.dumps(request_body, ensure_ascii=False)}

请根据测试计划与接口定义，生成 pytest + requests 测试代码（含 Allure 装饰器、参数化、断言）。必须返回 JSON：{{"code": "完整 test_*.py 的 Python 代码字符串"}}，code 内为可运行的 Python 代码。不要用 markdown 代码块包裹 JSON。"""
    code = ""
    try:
        result = await ai_client.chat(GENERATOR_SYSTEM_PROMPT, user_prompt)
        if isinstance(result, dict):
            code = result.get("code") or result.get("content") or result.get("test_code") or result.get("python_code") or ""
            if not code:
                for v in result.values():
                    if isinstance(v, str) and len(v) > 80 and ("def test_" in v or "import pytest" in v or "import requests" in v or "request." in v):
                        code = v
                        break
        if code and "```" in code:
            m = re.search(r"```(?:python)?\s*([\s\S]*?)```", code)
            if m:
                code = m.group(1).strip()
    except Exception:
        pass
    if not code or len(code) < 100:
        try:
            chat_raw = getattr(ai_client, "chat_raw", None)
            if callable(chat_raw):
                raw = await chat_raw(GENERATOR_SYSTEM_PROMPT, user_prompt)
                code = _extract_code_from_raw(raw)
        except Exception:
            pass
    if not code:
        code = "# 未生成测试代码，请检查接口定义或重试。\n# 可在此手写 pytest + requests 用例。"
    return code


# 主入口：优先用「测试计划 + 用例列表」生成 Playwright 代码；无 plan_payload 时退回 pytest
async def generate_playwright_code(
    ai_client: Any,
    plan_markdown: str,
    api_info: Dict[str, Any],
    plan_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generator Agent：解析测试计划，若有 plan_payload（含 endpoints[0].cases）则调用 api_generator 编排，
    使用 AI Prompt 生成 Playwright 接口测试文件；否则退回 generate_test_code（pytest）。
    """
    if plan_payload and (plan_payload.get("endpoints") or []):
        return await generate_playwright_code_from_plan(ai_client, plan_markdown, plan_payload)
    return await generate_test_code(ai_client, plan_markdown, api_info)


# ---------- 阶段 4：测试执行（Executor Agent） ----------


async def executor_agent(
    ai_client: Any,
    plan_markdown: str,
    cases_count: int,
    endpoints_summary: str = "",
) -> Dict[str, Any]:
    """
    阶段 4：调用测试执行 Agent 大模型，根据测试计划与用例数量给出执行策略说明。
    实际执行由 main_sqlite 的 _run_steps 完成；此处仅做策略/说明。
    """
    user_prompt = f"""测试计划摘要：
{plan_markdown[:2000] if plan_markdown else "无"}

将执行的用例数量：{cases_count}
接口摘要：{endpoints_summary or "单接口"}

请输出执行策略简要说明（JSON：execution_summary, cases_to_run）。"""
    out = await ai_client.chat(EXECUTOR_SYSTEM_PROMPT, user_prompt)
    if not isinstance(out, dict):
        out = {"execution_summary": str(out), "cases_to_run": cases_count}
    return out


# ---------- 阶段 5：结果分析（Analyzer Agent） ----------


async def analyze_suite_result(
    ai_client: Any,
    suite_result: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """
    阶段 5：调用结果分析 Agent 大模型，根据测试结果生成 Markdown 报告与图表数据。
    """
    total = suite_result.get("total_cases") or 0
    passed = suite_result.get("passed_cases") or 0
    failed = suite_result.get("failed_cases") or 0
    duration_ms = suite_result.get("duration_ms") or 0
    case_results = suite_result.get("case_results") or []

    chart_data = {
        "summary": {"total": total, "passed": passed, "failed": failed, "duration_ms": duration_ms},
        "pie": [{"name": "通过", "value": passed}, {"name": "失败", "value": failed}],
        "cases": [{"case_id": r.get("case_id"), "status": r.get("status"), "duration_ms": r.get("duration_ms")} for r in case_results],
    }

    user_prompt = json.dumps(
        {"total_cases": total, "passed_cases": passed, "failed_cases": failed, "duration_ms": duration_ms, "case_results": case_results},
        ensure_ascii=False,
        indent=2,
    )
    out = await ai_client.chat(ANALYZER_SYSTEM_PROMPT, user_prompt)
    if isinstance(out, dict):
        report_md = out.get("report") or out.get("content") or json.dumps(out, ensure_ascii=False)
    else:
        report_md = str(out)
    report_md = f"# 单接口测试结果分析\n\n{report_md}"
    return report_md, chart_data
