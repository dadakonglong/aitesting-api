from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import sys
import uvicorn
import sqlite3
import httpx
import urllib.parse
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv

# 保证从项目根或本目录运行都能找到 services / agents
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# 本地服务模块
from services.api_planner import ApiPlanner
from services.ai_case_generator import generate_cases_for_endpoint as ai_generate_cases_for_endpoint
from agents.healer import HealerAgent
from services.single_api_pipeline import (
    requirement_understanding,
    generate_test_plan_md,
    generate_playwright_code,
    generate_test_code,
    executor_agent,
    analyze_suite_result,
    rag_query_data,
)

# 加载环境变量
load_dotenv()

app = FastAPI(title="AI Testing API - Unified Edition")

from routers import api_management
app.include_router(api_management.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data/apis.db")

# ============= 模型适配层 =============

from openai import AsyncOpenAI
import re


def _parse_ai_json(content: str) -> Dict:
    """
    容错解析大模型返回的 JSON：空返回、顶层数组、markdown 包裹、尾部逗号、双引号转义等。
    解析失败时返回 {} 并打日志，不抛错，避免整次调用报「无法解析」。
    """
    if content is None:
        return {}
    raw = content.strip() if isinstance(content, str) else ""
    # 去掉 BOM / 不可见字符
    if raw.startswith("\ufeff"):
        raw = raw[1:].strip()
    if not raw:
        return {}
    
    # 预处理：修复常见的JSON格式问题
    def clean_json_string(s: str) -> str:
        """清理JSON字符串中的常见问题"""
        # 1. 修复双引号转义问题：""cases" -> "cases"（字段名被双引号包裹两次）
        # 匹配模式：""field_name" 或 ""field_name": 
        s = re.sub(r'""([a-zA-Z_][a-zA-Z0-9_]*)"(\s*:)', r'"\1"\2', s)
        # 2. 修复值中的双引号转义：""value" -> "value"
        s = re.sub(r':\s*""([^"]+)"([,\s}])', r': "\1"\2', s)
        # 3. 修复尾部逗号
        s = re.sub(r",\s*([}\]])", r"\1", s)
        # 4. 修复单引号（某些模型可能返回单引号）
        s = s.replace("'", '"')
        # 5. 移除控制字符（但保留换行符和制表符）
        s = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', s)
        return s
    
    # 1. 直接解析
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return {"cases": obj}
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    
    # 2. 清理后解析
    try:
        cleaned = clean_json_string(raw)
        obj = json.loads(cleaned)
        if isinstance(obj, list):
            return {"cases": obj}
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    
    # 3. 去掉 markdown 代码块
    if "```" in raw:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            try:
                inner = m.group(1).strip()
                cleaned_inner = clean_json_string(inner)
                obj = json.loads(cleaned_inner)
                if isinstance(obj, list):
                    return {"cases": obj}
                return obj if isinstance(obj, dict) else {}
            except json.JSONDecodeError:
                pass
    
    # 4. 顶层为数组：取 [ ... ] 解析后包装为 {"cases": ...}
    if raw.lstrip().startswith("["):
        start = raw.find("[")
        end = raw.rfind("]")
        if end > start:
            try:
                segment = raw[start : end + 1]
                cleaned_segment = clean_json_string(segment)
                obj = json.loads(cleaned_segment)
                return {"cases": obj} if isinstance(obj, list) else {}
            except json.JSONDecodeError:
                pass
    
    # 5. 取第一个 { 到最后一个 }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            segment = raw[start : end + 1]
            cleaned_segment = clean_json_string(segment)
            obj = json.loads(cleaned_segment)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            pass
    
    # 6. 尝试修复更多问题后解析
    for attempt in [raw, raw[start : end + 1] if start != -1 and end > start else raw]:
        fixed = clean_json_string(attempt)
        try:
            obj = json.loads(fixed)
            if isinstance(obj, list):
                return {"cases": obj}
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError as e:
            # 记录详细的错误信息
            error_pos = getattr(e, 'pos', None)
            if error_pos and error_pos < len(fixed):
                error_context = fixed[max(0, error_pos-50):error_pos+50]
                print(f"DEBUG: JSON解析错误位置 {error_pos}: ...{error_context}...")
    
    # 解析失败不抛错，返回空并打日志（便于排查「json 非法」指哪里）
    preview = (raw[:500] + "…") if len(raw) > 500 else raw
    print(f"⚠️ AI 返回无法解析为 JSON，已当空处理。")
    print(f"   内容预览（前500字符）: {preview!r}")
    print(f"   内容长度: {len(raw)} 字符")
    # 尝试输出更详细的错误信息
    try:
        json.loads(raw)  # 这会抛出详细的错误信息
    except json.JSONDecodeError as e:
        print(f"   JSON错误详情: {str(e)}")
        if hasattr(e, 'pos'):
            print(f"   错误位置: {e.pos}")
            if e.pos < len(raw):
                print(f"   错误位置上下文: {raw[max(0, e.pos-30):e.pos+30]!r}")
    return {}


class AIProvider:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.default_provider = os.getenv("AI_PROVIDER", "openai").lower()

    def get_client(self, provider: str) -> AsyncOpenAI:
        """根据供应商获取对应的 SDK 客户端 (强制禁用代理以解决 SSL 错误)"""
        # 创建一个干净的 http_client
        http_client = httpx.AsyncClient(
            timeout=60.0,
            trust_env=False,  # 禁用系统代理
            verify=True       # 保持 SSL 验证
        )
        
        if provider == "deepseek":
            return AsyncOpenAI(
                api_key=self.deepseek_key,
                base_url=self.deepseek_base_url,
                http_client=http_client
            )
        else:
            return AsyncOpenAI(
                api_key=self.openai_key,
                http_client=http_client
            )

    async def chat(self, system_prompt: str, user_prompt: str, provider: str = None) -> Dict:
        """使用 OpenAI SDK 调用接口（兼容 DeepSeek）"""
        active_provider = provider or self.default_provider
        client = self.get_client(active_provider)
        model = self.deepseek_model if active_provider == "deepseek" else self.openai_model

        print(f"📡 SDK 调用开始 | Provider: {active_provider} | Model: {model}")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            print(f"✅ AI 响应成功")
            if not response.choices or not response.choices[0].message:
                print("⚠️ AI 返回无内容，当空对象处理")
                return {}
            content = getattr(response.choices[0].message, "content", None) or ""
            if not (content and str(content).strip()):
                print("⚠️ AI 返回内容为空，当空对象处理")
                return {}
            return _parse_ai_json(str(content))
        except Exception as e:
            print(f"❌ AI 调用异常: {str(e)}")
            raise Exception(f"AI 服务不可用: {str(e)}")

    async def chat_raw(self, system_prompt: str, user_prompt: str, provider: str = None) -> str:
        """返回原始文本（不强制 JSON），用于需从 markdown/代码块中提取内容的场景（如代码生成）"""
        active_provider = provider or self.default_provider
        client = self.get_client(active_provider)
        model = self.deepseek_model if active_provider == "deepseek" else self.openai_model
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            if not response.choices or not response.choices[0].message:
                return ""
            content = getattr(response.choices[0].message, "content", None) or ""
            return str(content).strip()
        except Exception as e:
            print(f"❌ AI chat_raw 异常: {str(e)}")
            raise

ai_client = AIProvider()

# 初始化 API Planner（基于 apis.db 做接口测试计划）
api_planner = ApiPlanner(DB_PATH)
# API Healer（失败用例分析与自愈）
healer_agent = HealerAgent(ai_client, DB_PATH)

# ============= 数据库初始化 =============

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # API 表 (增强版)
    cursor.execute('''CREATE TABLE IF NOT EXISTS apis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        method TEXT NOT NULL,
        summary TEXT,
        description TEXT,
        base_url TEXT,
        parameters TEXT, -- JSON 存储
        request_body TEXT, -- JSON 存储
        headers TEXT, -- JSON 存储
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 自动迁移旧库：增加缺失的列
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN base_url TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN parameters TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN request_body TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN headers TEXT")
    except: pass
    
    # 场景表
    cursor.execute('''CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        natural_language_input TEXT,
        project_id TEXT DEFAULT 'default-project',
        nlu_result TEXT,
        test_case_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 测试用例表 (步骤序列) - 场景级用例
    cursor.execute('''CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        steps TEXT, -- JSON 存储步骤
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # API 级测试用例库（为单个接口保存的独立用例）
    cursor.execute('''CREATE TABLE IF NOT EXISTS api_test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        api_id INTEGER,
        method TEXT,
        path TEXT,
        source TEXT, -- ai / rule / manual
        case_type TEXT,
        name TEXT,
        description TEXT,
        request_template TEXT, -- JSON
        expected_template TEXT, -- JSON
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 执行记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_case_id INTEGER,
        status TEXT, -- success, fail, running
        results TEXT, -- JSON 存储各步详情
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    try:
        cursor.execute("ALTER TABLE executions ADD COLUMN project_id TEXT DEFAULT 'default-project'")
    except Exception:
        pass

    # 项目环境配置表
    cursor.execute('''CREATE TABLE IF NOT EXISTS project_environments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        env_name TEXT NOT NULL, -- 如 test, dev, prod
        base_url TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_id, env_name)
    )''')
    
    # 项目表
    cursor.execute('''CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Healer 修复记录表（用于场景用例自愈）
    cursor.execute('''CREATE TABLE IF NOT EXISTS healing_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_case_id INTEGER NOT NULL,
        original_steps TEXT,
        healed_steps TEXT,
        analysis TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # 接口测试报告表（执行后保存，供测试报告页面展示）
    cursor.execute('''CREATE TABLE IF NOT EXISTS test_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        report_type TEXT DEFAULT '接口测试',
        creator TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        end_time TEXT DEFAULT (datetime('now', 'localtime')),
        trigger_method TEXT DEFAULT '手动触发',
        status TEXT DEFAULT 'success',
        payload TEXT
    )''')

    # 定时任务表
    cursor.execute('''CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        project_id TEXT NOT NULL,
        scenario_id INTEGER NOT NULL,
        cron_expression TEXT NOT NULL,
        environment_id INTEGER,
        is_active INTEGER DEFAULT 1,
        notify_on_failure INTEGER DEFAULT 0,
        notification_config TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # 定时任务执行记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS job_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        status TEXT, -- success, failed, running
        started_at TEXT,
        completed_at TEXT,
        execution_id TEXT,
        total_steps INTEGER,
        passed_steps INTEGER,
        failed_steps INTEGER,
        error_message TEXT,
        FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id)
    )''')
    
    # 兼容性处理：如果 api 表中存在 default-project 但 projects 表中没有，则插入
    cursor.execute("SELECT COUNT(*) FROM projects WHERE id = 'default-project'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO projects (id, name, description) VALUES ('default-project', '默认项目', '系统自动创建的默认项目')")

    conn.commit()
    conn.close()
    print(f"✅ 数据库架构已就绪: {DB_PATH}")

init_database()

# ============= 核心业务路由 =============

# --- 场景与用例生成 ---

class ScenarioCreateRequest(BaseModel):
    natural_language_input: str
    project_id: str = "default-project"

@app.post("/api/v1/scenarios")
async def create_scenario(req: ScenarioCreateRequest):
    """场景理解并搜索 API"""
    try:
        print(f"🔍 收到场景创建请求: {req.natural_language_input}")
        # 1. AI 理解意图
        system_prompt = "你是一个接口测试专家。请解析用户描述的测试场景，提取意图、涉及实体和动作序列。以 JSON 格式返回：{intent, entities, actions, expected_results}"
        nlu_result = await ai_client.chat(system_prompt, req.natural_language_input)
        print(f"✅ AI 理解完成: {nlu_result.get('intent')}")
        
        # 2. 保存场景
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scenarios (name, natural_language_input, nlu_result, project_id) VALUES (?, ?, ?, ?)",
            (nlu_result.get("intent", "未命名场景"), req.natural_language_input, json.dumps(nlu_result), req.project_id)
        )
        scenario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"id": scenario_id, "name": nlu_result.get("intent"), "description": req.natural_language_input}
    except Exception as e:
        print(f"❌ 场景创建失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: int):
    """删除场景及其关联的测试用例"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取关联的 test_case_id
        cursor.execute("SELECT test_case_id FROM scenarios WHERE id = ?", (scenario_id,))
        row = cursor.fetchone()
        
        # 删除场景
        cursor.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        
        # 如果有测试用例，也一并删除
        if row and row[0]:
            cursor.execute("DELETE FROM test_cases WHERE id = ?", (row[0],))
            
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 单接口 AI 测试流水线（五阶段） =============

class SingleApiUnderstandRequest(BaseModel):
    """阶段1：需求理解"""
    natural_language_input: str
    project_id: str = "default-project"


class SingleApiPlanRequest(BaseModel):
    """阶段2：测试计划（可传入阶段1输出或直接 api_id）"""
    project_id: str = "default-project"
    structured_info: Optional[Dict[str, Any]] = None  # 阶段1输出
    api_id: Optional[int] = None  # 或直接指定接口 id


class SingleApiGenerateCodeRequest(BaseModel):
    """阶段3：代码生成（可选 plan_payload 时按用例列表生成 Playwright）"""
    plan_markdown: str
    api_info: Dict[str, Any]
    plan_payload: Optional[Dict[str, Any]] = None


class SingleApiExecuteRequest(BaseModel):
    """阶段4：执行（优先用生成代码解析出的用例，否则用计划中的 endpoints 或 steps）"""
    project_id: str = "default-project"
    base_url: str = ""
    environment: str = "test"
    plan: Optional[Dict[str, Any]] = None  # 含 endpoints[].cases 的计划
    steps: Optional[List[Dict[str, Any]]] = None  # 或直接步骤列表
    generated_code: Optional[str] = None  # 生成的 Playwright 代码，若提供则优先从中解析用例再执行


class SingleApiAnalyzeRequest(BaseModel):
    """阶段5：结果分析"""
    suite_result: Dict[str, Any]  # 阶段4 执行返回的汇总结果


class SingleApiFullPipelineRequest(BaseModel):
    """一键完整流水线"""
    natural_language_input: str
    project_id: str = "default-project"
    base_url: str = ""
    environment: str = "test"
    run_execution: bool = True  # 是否执行并分析；False 则只做到代码生成


@app.post("/api/v1/single-api/understand")
async def single_api_understand(req: SingleApiUnderstandRequest):
    """阶段1：需求理解 — 解析用户意图 + RAG 检索，返回结构化 API 信息"""
    try:
        result = await requirement_understanding(
            ai_client, req.natural_language_input, req.project_id, DB_PATH
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _safe_json(s: Any, default: Any = None) -> Any:
    if not s:
        return True # Treat empty as safe to default logic
    try:
        json.loads(s)
        return True
    except:
        return False

@app.post("/api/v1/single-api/plan")
async def single_api_plan(req: SingleApiPlanRequest):
    """阶段2：测试计划 — 根据结构化信息或 api_id 生成 Markdown 测试计划"""
    try:
        if req.api_id is not None:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, path, method, summary, description, base_url, parameters, request_body, headers FROM apis WHERE id = ? AND project_id = ?",
                (req.api_id, req.project_id),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                raise HTTPException(status_code=404, detail="接口不存在")
            api_candidates = [{
                "id": row["id"], "path": row["path"], "method": row["method"],
                "summary": row["summary"], "description": row["description"],
                "base_url": row["base_url"],
                "parameters": json.loads(row["parameters"] or "[]") if _safe_json(row["parameters"]) else [],
                "request_body": json.loads(row["request_body"] or "{}") if _safe_json(row["request_body"], default="{}") else {},
                "headers": json.loads(row["headers"] or "{}") if _safe_json(row["headers"], default="{}") else {},
            }]
            structured_info = {"api_candidates": api_candidates, "entities": [], "chunks": []}
        else:
            structured_info = req.structured_info or {}
        plan_md, plan_payload = await generate_test_plan_md(
            ai_client, structured_info, api_planner, req.project_id
        )
        return {"markdown": plan_md, "plan": plan_payload}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/single-api/generate-code")
async def single_api_generate_code(req: SingleApiGenerateCodeRequest):
    """阶段3：代码生成 — 根据测试计划与接口信息生成 Playwright 测试文件内容"""
    try:
        code = await generate_playwright_code(
            ai_client, req.plan_markdown, req.api_info, req.plan_payload
        )
        return {"code": code, "filename": "api.spec.ts"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _plan_has_cases(plan: Optional[Dict[str, Any]]) -> bool:
    """检查 plan 是否包含可执行用例"""
    if not plan:
        return False
    for ep in plan.get("endpoints") or []:
        cases = ep.get("cases") or []
        if cases:
            return True
    return False


def _single_api_plan_to_steps(plan: Dict[str, Any]) -> List[Dict]:
    """将计划中的 endpoints[].cases 转为 _run_steps 所需的 steps（支持单接口和多接口）"""
    endpoints = plan.get("endpoints") or []
    if not endpoints:
        return []
    steps = []
    step_order = 1
    for ep in endpoints:
        path = ep.get("path") or ""
        method = (ep.get("method") or "GET").upper()
        base_url_ep = (ep.get("base_url") or "").strip()
        for c in ep.get("cases") or []:
            rt = c.get("request_template") or {}
            et = c.get("expected_template") or {}
            steps.append({
                "step_order": step_order,
                "api_path": path,
                "api_method": method,
                "params": rt.get("params") or {},
                "url_params": rt.get("url_params") or {},
                "headers": rt.get("headers") or {},
                "param_mappings": [],
                "base_url": base_url_ep,
                "expected_status": et.get("status_code", 200),
                "expected_response_body": et.get("response_body") or et.get("expected_response") or {},
            })
            step_order += 1
    return steps


_CASE_TYPE_CN = {"positive": "正向", "boundary": "边界", "robustness": "健壮", "security": "安全"}


def _enrich_step_results_with_plan(step_results: List[Dict], plan: Optional[Dict] = None) -> None:
    """用计划中的用例名称和 request_template 补全每条执行结果，便于前端显示「正向/边界/健壮」等名称及请求头/body。"""
    if not plan:
        return
    plan_cases = []
    for ep in plan.get("endpoints") or []:
        plan_cases.extend(ep.get("cases") or [])
    for i, sr in enumerate(step_results):
        if i < len(plan_cases):
            pc = plan_cases[i]
            name_from_plan = (pc.get("name") or "").strip()
            # 若计划中无名称或为英文类型名（如 [positive]），用中文类型 + 方法路径 生成名称
            if not name_from_plan or any(name_from_plan.startswith(f"[{t}]") for t in _CASE_TYPE_CN):
                ct = (pc.get("case_type") or "positive").lower()
                if hasattr(ct, "value"):
                    ct = getattr(ct, "value", ct)
                type_cn = _CASE_TYPE_CN.get(ct, ct)
                path = pc.get("path") or ""
                if not path:
                    for ep in plan.get("endpoints") or []:
                        if pc in (ep.get("cases") or []):
                            path = ep.get("path") or ""
                            break
                method = (pc.get("method") or "GET").upper()
                name_from_plan = f"[{type_cn}] {method} {path}".strip()
            sr["name"] = name_from_plan or sr.get("name") or f"步骤{i + 1}"
            rt = pc.get("request_template") or {}
            if not (sr.get("request_data") or {}):
                sr["request_data"] = rt.get("params") or {}
            if not (sr.get("request_headers") or {}):
                sr["request_headers"] = rt.get("headers") or {}
        else:
            sr["name"] = sr.get("name") or f"步骤{i + 1}"


def _parse_js_like_object(s: str) -> Optional[Dict]:
    """尝试将 JS 风格对象字符串解析为 dict，支持 { key: 'val' } 和标准 JSON"""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s.startswith("{"):
        return None
    # 1) 直接 JSON 解析
    try:
        return json.loads(s)
    except Exception:
        pass
    # 2) 单引号改双引号后再试（简单替换可能破坏字符串内的引号，仅对简单结构有效）
    try:
        t = s.replace("'", '"')
        return json.loads(t)
    except Exception:
        pass
    # 3) 将未加引号的键名加上双引号：, key : -> , "key" :
    try:
        t = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)", r'\1"\2"\3', s)
        t = t.replace("'", '"')
        return json.loads(t)
    except Exception:
        pass
    return None


def _parse_playwright_code_to_steps(
    code: str, plan_fallback: Optional[Dict[str, Any]] = None
) -> List[Dict]:
    """
    从生成的 Playwright 代码中解析出用例步骤，使「执行」与「代码里的用例」一致。
    解析 path/method 与每个 test 的 request 选项；若某条解析不到 data 则用 plan_fallback 中对应用例补全。
    """
    if not code or not isinstance(code, str):
        return []
    code = code.strip()
    # 1) 解析 API_PATH、BASE_URL（可选）
    api_path = ""
    for m in re.finditer(r"(?:const|let)\s+API_PATH\s*=\s*['\"]([^'\"]+)['\"]", code):
        api_path = m.group(1).strip()
        break
    if not api_path:
        for m in re.finditer(r"request\.(post|get)\s*\(\s*['\"]([^'\"]+)['\"]", code):
            first_arg = m.group(2).strip()
            if first_arg.startswith("http"):
                api_path = re.sub(r"^https?://[^/]+", "", first_arg) or "/"
            else:
                api_path = first_arg if first_arg.startswith("/") else "/" + first_arg
            break
    if not api_path:
        for m in re.finditer(r"request\.(post|get)\s*\(\s*`([^`]+)`", code):
            # 模板字符串可能含 ${BASE_URL}${API_PATH}
            tpl = m.group(2)
            if "API_PATH" in tpl:
                for m2 in re.finditer(r"(?:const|let)\s+API_PATH\s*=\s*['\"]([^'\"]+)['\"]", code):
                    api_path = m2.group(1).strip()
                    break
            break
    if not api_path:
        api_path = "/"
    # 2) 按 plan_fallback 构建「用例索引 -> (path, method)」映射，支持多接口
    plan_endpoints = (plan_fallback or {}).get("endpoints") or []
    def step_to_ep_info(step_idx: int):
        idx = step_idx
        for ep in plan_endpoints:
            cases = ep.get("cases") or []
            if idx < len(cases):
                path = ep.get("path") or ""
                m = (ep.get("method") or "GET").upper()
                return path if path.startswith("/") else "/" + path.lstrip("/"), m
            idx -= len(cases)
        return api_path, "POST"

    method = "POST"
    steps = []
    # 按 test( 切分，每个块里找 request.post/get
    blocks = re.split(r"\btest\s*\([\s\S]*?async\s*\([^)]*\)\s*=>\s*\{", code)
    for bi, block in enumerate(blocks):
        if bi == 0:
            continue
        # 在块内找 request.(post|get)( ... , { ... })
        mo = re.search(r"request\.(post|get)\s*\(\s*[^,]+,?\s*\{", block)
        if not mo:
            continue
        method = mo.group(1).upper()
        # 支持多接口：从 plan 按顺序映射 path；或尝试从代码解析字面量 path
        block_path = api_path
        if plan_endpoints:
            block_path, method = step_to_ep_info(bi - 1)
        else:
            path_mo = re.search(r'request\.(post|get)\s*\(\s*["\']([^"\']+)["\']', block)
            if path_mo:
                pa = path_mo.group(2).strip()
                if pa.startswith("http"):
                    block_path = re.sub(r"^https?://[^/]+", "", pa) or "/"
                elif pa:
                    block_path = pa if pa.startswith("/") else "/" + pa
        start = mo.start()
        brace_start = block.index("{", start)
        depth = 1
        i = brace_start + 1
        while i < len(block) and depth > 0:
            if block[i] == "{":
                depth += 1
            elif block[i] == "}":
                depth -= 1
            i += 1
        opts_str = block[brace_start:i]
        params = {}
        url_params = {}
        headers = {}
        # 从 opts_str 中提取 data/form/formData: { ... } 和 headers: { ... }
        for data_key in ("data", "form", "formData"):
            data_m = re.search(rf"{data_key}\s*:\s*(\{{(?:[^{{}}]|\{{[^{{}}]*\}})*\}})", opts_str)
            if data_m:
                parsed = _parse_js_like_object(data_m.group(1))
                if parsed and isinstance(parsed, dict):
                    params = parsed
                    break
        headers_m = re.search(r"headers\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})", opts_str)
        if headers_m:
            parsed = _parse_js_like_object(headers_m.group(1))
            if parsed and isinstance(parsed, dict):
                headers = parsed
        # 始终用 plan 的 request_template 作为权威来源（测试用例由 plan 生成，body/headers 必须一致）
        rt = {}
        step_idx = bi - 1
        idx = step_idx
        for ep in plan_endpoints:
            cases = ep.get("cases") or []
            if idx < len(cases):
                rt = cases[idx].get("request_template") or {}
                break
            idx -= len(cases)
        if rt:
            # plan 有数据时，以 plan 为准（测试用例由 plan 生成，请求内容必须与 plan 一致）
            params = rt.get("params") or params or {}
            url_params = rt.get("url_params") or {}
            headers = rt.get("headers") or headers or {}
        steps.append({
            "step_order": len(steps) + 1,
            "api_path": block_path,
            "api_method": method,
            "params": params,
            "url_params": url_params,
            "headers": headers,
            "param_mappings": [],
            "base_url": "",
        })
    return steps


@app.post("/api/v1/single-api/execute")
async def single_api_execute(req: SingleApiExecuteRequest):
    """阶段4：执行 — 根据计划或步骤列表执行，返回 suite 结果（供阶段5 分析）"""
    try:
        base_url = (req.base_url or "").strip()
        if not base_url:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT base_url FROM project_environments WHERE project_id = ? AND (env_name = ? OR is_default = 1) ORDER BY is_default DESC LIMIT 1",
                (req.project_id, req.environment),
            )
            row = cursor.fetchone()
            conn.close()
            base_url = (row["base_url"] or "").strip() if row else ""
        if not base_url:
            raise HTTPException(
                status_code=400,
                detail="请配置接口基础地址：在「再次执行并分析」旁的输入框填写 base_url（如 https://api.example.com），或在项目环境中配置 base_url。",
            )

        if req.steps:
            steps = req.steps
        elif req.plan and _plan_has_cases(req.plan):
            # 有 plan 且含用例时，直接用 plan 构建步骤（保证请求 body/headers/params 为真实数据，与 API 管理单测一致）
            steps = _single_api_plan_to_steps(req.plan)
        elif (req.generated_code or "").strip():
            # 无有效 plan 时，从生成代码解析
            steps = _parse_playwright_code_to_steps(req.generated_code.strip(), req.plan)
            if not steps and req.plan:
                steps = _single_api_plan_to_steps(req.plan)
        elif req.plan:
            # Debug: 写日志文件
            try:
                eps = req.plan.get("endpoints") or []
                log_msg = f"EXECUTE DEBUG: endpoints_count={len(eps)}"
                if eps:
                    c = eps[0].get("cases") or []
                    log_msg += f", case_count={len(c)}"
                    if c:
                        log_msg += f", first_case_keys={list(c[0].keys())}"
                
                with open("pipeline_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] {log_msg}\n")
            except Exception as e:
                print(f"DEBUG: log error {e}")

            steps = _single_api_plan_to_steps(req.plan)
            # 若计划中用例为空（如旧数据或持久化丢失），尝试从 ApiPlanner / ai_generate_cases 补全后再执行
            if not steps and req.plan:
                endpoints = req.plan.get("endpoints") or []
                if endpoints:
                    ep = endpoints[0]
                    path = ep.get("path") or ""
                    method = (ep.get("method") or "GET").upper()
                    plan_full = api_planner.generate_plan(project_id=req.project_id)
                    for e in plan_full.get("endpoints") or []:
                        if (e.get("path") == path and
                                (e.get("method") or "GET").upper() == method):
                            ep["cases"] = e.get("cases") or []
                            break
                    if not ep.get("cases"):
                        try:
                            cases = await ai_generate_cases_for_endpoint(
                                ai_client,
                                {
                                    "path": path,
                                    "method": method,
                                    "summary": ep.get("summary"),
                                    "description": ep.get("description"),
                                    "parameters": ep.get("parameters"),
                                    "request_body": ep.get("request_body"),
                                },
                                include_types=["positive", "boundary", "robustness", "security"],
                            )
                            ep["cases"] = cases
                        except Exception as _e:
                            print(f"DEBUG: ai_generate_cases fallback failed: {_e}")
                    steps = _single_api_plan_to_steps(req.plan)
        else:
            raise HTTPException(status_code=400, detail="请提供 plan 或 steps")

        if not steps:
            with open("pipeline_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] EXECUTE ERROR: Steps empty after conversion!\n")
            print("DEBUG: Steps are empty after conversion!")
            raise HTTPException(
                status_code=400,
                detail="计划中无可用用例（endpoints 中无 cases）。请重新在「AI生成」中生成接口用例后再执行。",
            )

        start_ts = datetime.now()
        step_results = await _run_steps(steps, base_url)
        duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
        # 用计划中的用例名称和 request_template 补全每条结果，前端可显示「正向/边界/健壮」等及请求头/body
        _enrich_step_results_with_plan(step_results, req.plan)

        passed = sum(1 for s in step_results if s.get("success"))
        failed = len(step_results) - passed
        case_results = []
        for i, s in enumerate(step_results):
            case_results.append({
                "case_id": f"TC{i+1:03d}",  # 与生成代码中的 TC001/TC002 格式一致
                "status": "passed" if s.get("success") else "failed",
                "duration_ms": int((s.get("duration") or 0) * 1000),
            })

        suite_result = {
            "suite_id": "single-api-suite",
            "total_cases": len(step_results),
            "passed_cases": passed,
            "failed_cases": failed,
            "duration_ms": duration_ms,
            "case_results": case_results,
            "results": step_results,
        }
        return suite_result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/single-api/analyze")
async def single_api_analyze(req: SingleApiAnalyzeRequest):
    """阶段5：结果分析 — 根据执行结果生成 Markdown 报告与图表数据"""
    try:
        report_md, chart_data = await analyze_suite_result(ai_client, req.suite_result)
        return {"report": report_md, "chart_data": chart_data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/single-api/full-pipeline")
async def single_api_full_pipeline(req: SingleApiFullPipelineRequest):
    """单接口完整流水线：需求理解 -> 测试计划 -> 代码生成 -> [执行 -> 结果分析]"""
    try:
        # 1. 需求理解
        structured = await requirement_understanding(
            ai_client, req.natural_language_input, req.project_id, DB_PATH
        )
        # 2. 测试计划
        plan_md, plan_payload = await generate_test_plan_md(
            ai_client, structured, api_planner, req.project_id
        )
        target_api = (plan_payload.get("endpoints") or [{}])[0] if plan_payload.get("endpoints") else {}
        api_info = plan_payload.get("target_api") or target_api
        if not api_info:
            api_info = (structured.get("api_candidates") or [{}])[0] or {}
        # 3. 代码生成：Generator Agent 解析测试计划 + plan_payload 用例列表，生成 Playwright 测试文件
        code = await generate_playwright_code(ai_client, plan_md, api_info, plan_payload)

        out = {
            "phase1_structured": structured,
            "phase2_plan_markdown": plan_md,
            "phase2_plan": plan_payload,
            "phase3_code": code,
            "phase4_executor_summary": None,
            "phase4_result": None,
            "phase5_report": None,
            "phase5_chart_data": None,
        }

        if req.run_execution and plan_payload.get("endpoints"):
            endpoints = plan_payload.get("endpoints") or []
            cases_count = sum(len(ep.get("cases") or []) for ep in endpoints)
            ep_summary = "; ".join(f"{ep.get('method')} {ep.get('path')}" for ep in endpoints[:3])
            try:
                executor_out = await executor_agent(ai_client, plan_md, cases_count, ep_summary)
                out["phase4_executor_summary"] = executor_out
            except Exception as _e:
                out["phase4_executor_summary"] = {"execution_summary": f"执行策略生成异常: {_e}", "cases_to_run": cases_count}

            base_url = (req.base_url or "").strip()
            if not base_url:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # 1) 优先：env_name=environment 或 is_default=1
                cursor.execute(
                    "SELECT base_url FROM project_environments WHERE project_id = ? AND (env_name = ? OR is_default = 1) ORDER BY is_default DESC LIMIT 1",
                    (req.project_id, req.environment),
                )
                row = cursor.fetchone()
                if row:
                    base_url = (row["base_url"] or "").strip()
                # 2) 兜底：该项目下任意环境
                if not base_url:
                    cursor.execute(
                        "SELECT base_url FROM project_environments WHERE project_id = ? AND base_url IS NOT NULL AND base_url != '' ORDER BY is_default DESC, id LIMIT 1",
                        (req.project_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        base_url = (row["base_url"] or "").strip()
                conn.close()
            if base_url:
                steps = _single_api_plan_to_steps(plan_payload)
                if steps:
                    start_ts = datetime.now()
                    step_results = await _run_steps(steps, base_url)
                    duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
                    _enrich_step_results_with_plan(step_results, plan_payload)
                    passed = sum(1 for s in step_results if s.get("success"))
                    suite_result = {
                        "suite_id": "single-api-suite",
                        "total_cases": len(step_results),
                        "passed_cases": passed,
                        "failed_cases": len(step_results) - passed,
                        "duration_ms": duration_ms,
                        "case_results": [
                            {"case_id": f"TC{i+1:02d}", "status": "passed" if s.get("success") else "failed", "duration_ms": int((s.get("duration") or 0) * 1000)}
                            for i, s in enumerate(step_results)
                        ],
                        "results": step_results,
                    }
                    out["phase4_result"] = suite_result
                    report_md, chart_data = await analyze_suite_result(ai_client, suite_result)
                    out["phase5_report"] = report_md
                    out["phase5_chart_data"] = chart_data
        return out
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- 环境配置管理 ---

class EnvironmentBase(BaseModel):
    env_name: str
    base_url: str
    is_default: Optional[bool] = False

@app.get("/api/v1/projects/{project_id}/environments")
async def list_environments(project_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_environments WHERE project_id = ?", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/projects/{project_id}/environments")
async def save_environment(project_id: str, env: EnvironmentBase):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 如果标记为默认，先取消该项目其他默认
        if env.is_default:
            cursor.execute("UPDATE project_environments SET is_default = 0 WHERE project_id = ?", (project_id,))
            
        cursor.execute("""
            INSERT INTO project_environments (project_id, env_name, base_url, is_default)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, env_name) DO UPDATE SET
                base_url = excluded.base_url,
                is_default = excluded.is_default
        """, (project_id, env.env_name, env.base_url, 1 if env.is_default else 0))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    return {"success": True}

@app.delete("/api/v1/projects/{project_id}/environments/{env_name}")
async def delete_environment(project_id: str, env_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_environments WHERE project_id = ? AND env_name = ?", (project_id, env_name))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/v1/scenarios")
async def list_scenarios():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, t.steps as test_case_steps 
        FROM scenarios s 
        LEFT JOIN test_cases t ON s.test_case_id = t.id 
        ORDER BY s.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/scenarios/{scenario_id}/generate-case")
async def generate_case(scenario_id: int):
    """从海量 API 中检索并智能编排用例链"""
    try:
        def _safe_json_loads(val, default):
            if val is None:
                return default
            if isinstance(val, (dict, list)):
                return val
            if isinstance(val, str):
                s = val.strip()
                if not s:
                    return default
                try:
                    return json.loads(s)
                except Exception:
                    return default
            return default

        def _normalize_headers_dict(h):
            if not isinstance(h, dict):
                return {}
            out = {}
            for k, v in h.items():
                if k is None:
                    continue
                key = str(k).strip()
                if not key:
                    continue
                # 统一为字符串，避免 httpx header 类型问题
                out[key] = "" if v is None else str(v)
            return out

        def _has_mapping(mappings, to_field, to_type="headers"):
            for m in mappings or []:
                if not isinstance(m, dict):
                    continue
                if (m.get("to_field") == to_field) and (m.get("to_type", "params") == to_type):
                    return True
            return False

        def _ensure_header_mapping(mappings, from_step, from_fields, to_field):
            """允许多个候选 from_field：前面的失败了，后面的仍可能成功"""
            if mappings is None:
                mappings = []
            if not isinstance(mappings, list):
                mappings = []
            if _has_mapping(mappings, to_field, "headers"):
                return mappings
            for f in from_fields:
                mappings.append({
                    "from_step": from_step,
                    "from_field": f,
                    "to_field": to_field,
                    "to_type": "headers"
                })
            return mappings

        def _enhance_steps_with_headers(project_id: str, steps: List[Dict[str, Any]], cursor):
            """生成用例后，自动补齐 headers + 动态依赖（如 token、员工/门店ID、sessionId 等）的 param_mappings。"""
            if not isinstance(steps, list) or not steps:
                return steps

            # 取出项目下所有 API 的 headers 定义，按 (method,path) 建索引
            cursor.execute(
                "SELECT path, method, headers FROM apis WHERE project_id = ?",
                (project_id,)
            )
            api_rows = cursor.fetchall()
            api_headers_by_key = {}
            for r in api_rows:
                try:
                    p = r["path"] if isinstance(r, sqlite3.Row) else r[0]
                    m = r["method"] if isinstance(r, sqlite3.Row) else r[1]
                    h = r["headers"] if isinstance(r, sqlite3.Row) else r[2]
                except Exception:
                    continue
                api_headers_by_key[(str(m or "").upper(), str(p or ""))] = _normalize_headers_dict(_safe_json_loads(h, {}))

            # 约定：第 1 步通常是登录/获取 token（从该步提取动态头）
            from_step_for_auth = 1

            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue

                method = str(step.get("api_method") or step.get("method") or "GET").upper()
                path = step.get("api_path") or step.get("path") or ""
                key = (method, str(path))

                headers = _normalize_headers_dict(step.get("headers") or {})
                params_body = step.get("params") if isinstance(step.get("params"), dict) else {}
                param_mappings = step.get("param_mappings")
                if not isinstance(param_mappings, list):
                    param_mappings = []

                # 1) 合并 API 定义中的 headers（不覆盖用户已有；跳过 Authorization 静态值）
                api_headers = api_headers_by_key.get(key) or {}
                for hk, hv in api_headers.items():
                    if hk.lower() == "authorization":
                        continue
                    if hk not in headers and hv:
                        headers[hk] = hv

                # 2) 如果 headers 里出现 ${...} 占位符，清理掉，避免“看起来有值但执行时无效”
                for hk in list(headers.keys()):
                    hv = headers.get(hk, "")
                    if isinstance(hv, str) and ("${" in hv or "{{" in hv):
                        # Authorization 必须靠 param_mappings 注入
                        if hk.lower() == "authorization":
                            headers.pop(hk, None)

                # 3) 动态头自动补齐（优先用 step.params 的静态值；否则用 param_mappings 从第1步提取）
                if "X-Venue-Id" not in headers:
                    if isinstance(params_body, dict) and params_body.get("venueId"):
                        headers["X-Venue-Id"] = str(params_body.get("venueId"))
                    else:
                        param_mappings = _ensure_header_mapping(
                            param_mappings,
                            from_step_for_auth,
                            ["data.venueId", "data.user.venueId", "data.profile.venueId"],
                            "X-Venue-Id"
                        )

                if "X-Employee-Id" not in headers:
                    if isinstance(params_body, dict) and params_body.get("employeeId"):
                        headers["X-Employee-Id"] = str(params_body.get("employeeId"))
                    else:
                        param_mappings = _ensure_header_mapping(
                            param_mappings,
                            from_step_for_auth,
                            ["data.employeeId", "data.user.employeeId", "data.profile.employeeId", "data.empId"],
                            "X-Employee-Id"
                        )

                # Authorization：无论 API 定义里有没有，都确保通过映射注入
                param_mappings = _ensure_header_mapping(
                    param_mappings,
                    from_step_for_auth,
                    ["data.token", "token", "data.access_token", "data.accessToken"],
                    "Authorization"
                )

                # 4) 常见 body 依赖自动补齐：sessionId
                # 典型链路：步骤2 open-pay 返回 data.sessionId，步骤3 close-room 需要该 sessionId
                current_step_order = step.get("step_order") or (i + 1)
                if isinstance(params_body, dict) and "sessionId" in params_body and int(current_step_order) > 1:
                    # 只有在尚未配置映射时才自动添加，避免覆盖人工配置
                    if not _has_mapping(param_mappings, "sessionId", to_type="params"):
                        from_step_for_session = int(current_step_order) - 1
                        # 优先尝试 data.sessionId；若不存在，执行时会回退为原始静态值
                        param_mappings.append({
                            "from_step": from_step_for_session,
                            "from_field": "data.sessionId",
                            "to_field": "sessionId",
                            "to_type": "params"
                        })

                # 5) 通用 body 依赖自动补齐：同名字段 data.xxx -> params.xxx
                # 只对第2步及之后生效，且不会覆盖已有人工映射
                if isinstance(params_body, dict) and int(current_step_order) > 1:
                    from_step_for_generic = int(current_step_order) - 1
                    for field_name in list(params_body.keys()):
                        # 已有专门逻辑或已配置映射的字段跳过
                        if field_name in ("sessionId",):
                            continue
                        if _has_mapping(param_mappings, field_name, to_type="params"):
                            continue
                        # 自动假定上一步响应中存在 data.<field_name>
                        param_mappings.append({
                            "from_step": from_step_for_generic,
                            "from_field": f"data.{field_name}",
                            "to_field": field_name,
                            "to_type": "params"
                        })

                step["headers"] = headers
                step["param_mappings"] = param_mappings

            return steps

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取场景信息
        cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
        scenario = cursor.fetchone()
        if not scenario: raise HTTPException(status_code=404, detail="场景不存在")
        
        # 2. RAG: 简易语义检索 (包含完整参数和请求体以供 AI 精准识别)
        cursor.execute("""
            SELECT path, method, summary, description, base_url, parameters, request_body, headers
            FROM apis 
            WHERE project_id = ?
        """, (scenario["project_id"],))
        rows_apis = cursor.fetchall()
        all_apis = [dict(row) for row in rows_apis]
        
        # 3. AI 编排 (增强版 - 智能识别参数依赖)
        system_prompt = """你是个资深自动化专家。任务：根据【业务意图】和【API列表】，生成 JSON 测试步骤。
关键规则：
1. 必须识别依赖：若 A 返回 data.token，B 需使用，则配置 param_mappings。
2. 特别是鉴权：登录返回的 Token 必须映射到后续接口的 Headers，to_field 通常为 "Authorization"，to_type 为 "headers"。
3. 禁止自引用：步骤N不能引用步骤N自己的数据，from_step必须小于当前步骤。
4. 第一步通常无依赖：第一个步骤（通常是登录）的param_mappings应该为空[]。
5. 字段区分：params 放 Body (POST/PUT)，url_params 放 Query String。
6. 真实数据：生成符合逻辑的姓名、手机号等，不要用 {}。
格式：{ "scenario_name": "...", "steps": [{ "step_order": 1, "api_path": "...", "api_method": "...", "params": {}, "url_params": {}, "headers": {}, "param_mappings": [{ "from_step": 1, "from_field": "data.token", "to_field": "Authorization", "to_type": "headers" }] }] }"""
        
        user_prompt = f"意图: {scenario['nlu_result']}\n可用 API: {json.dumps(all_apis[:50])}" 
        case_result = await ai_client.chat(system_prompt, user_prompt)

        # 3.5 生成后增强：自动合并 API headers，并补齐动态头映射（避免漏 X-Employee-Id / X-Venue-Id 等）
        try:
            steps = case_result.get("steps") if isinstance(case_result, dict) else None
            if isinstance(steps, list):
                case_result["steps"] = _enhance_steps_with_headers(scenario["project_id"], steps, cursor)
        except Exception as _e:
            # 不阻断主流程：增强失败时仍保存 AI 产物
            print(f"DEBUG: enhance steps headers failed: {str(_e)}")
        
        # 4. 保存测试用例
        cursor.execute(
            "INSERT INTO test_cases (name, steps, project_id) VALUES (?, ?, ?)",
            (case_result.get("scenario_name"), json.dumps(case_result.get("steps")), scenario["project_id"])
        )
        case_id = cursor.lastrowid
        cursor.execute("UPDATE scenarios SET test_case_id = ? WHERE id = ?", (case_id, scenario_id))
        conn.commit()
        conn.close()
        return {**case_result, "name": case_result.get("scenario_name"), "id": case_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 执行引擎 ---

class ExecutionRequest(BaseModel):
    test_case_id: Optional[int] = None
    steps: Optional[List[Any]] = None  # 支持直接传入步骤执行
    environment: str = "test"
    base_url: str = "http://localhost:8000"


def _get_value_by_path(data, path):
    """支持 a.b.c 路径提取"""
    if data is None or not path:
        return None
    parts = path.split(".")
    curr = data
    for p in parts:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        elif isinstance(curr, list) and p.isdigit():
            idx = int(p)
            if idx < len(curr):
                curr = curr[idx]
            else:
                return None
        else:
            return None
    return curr


async def _run_steps(steps: List[Dict], base_url: str) -> List[Dict]:
    """执行步骤列表，返回每条步骤的请求/响应与 success（按 status_code < 400 判定）。"""
    context = {}
    step_results = []
    base_url = (base_url or "http://localhost:8000").strip()

    async with httpx.AsyncClient(verify=False) as client:
        for i, step in enumerate(steps):
            step_order = step.get("step_order", i + 1)
            print(f"DEBUG: Starting step {step_order} [{step.get('api_method', 'GET')} {step.get('api_path')}]")
            start_time = datetime.now()
            current_base_url = (step.get("base_url") or "").strip() or base_url or "http://localhost:8000"
            step_data = {
                "step_order": step_order,
                "url": "",
                "method": step.get("api_method", step.get("method", "GET")).upper(),
                "request_data": (step.get("params") or {}).copy(),
                "url_params": (step.get("url_params") or {}).copy(),
                "request_headers": (step.get("headers") or {}).copy(),
                "success": False,
                "status_code": "Error",
            }
            try:
                api_path = step.get("api_path", step.get("path", ""))
                safe_path = urllib.parse.quote(api_path.lstrip("/"), safe="/?=&")
                url = f"{current_base_url.rstrip('/')}/{safe_path}"
                step_data["url"] = url
                params_body = (step.get("params") or {}).copy()
                params_query = (step.get("url_params") or {}).copy()
                request_headers = (step.get("headers") or {}).copy()
                method = step_data["method"]
                extractions = []
                for mapping in step.get("param_mappings", []):
                    from_step_idx = mapping.get("from_step")
                    from_field = mapping.get("from_field")
                    to_field = mapping.get("to_field")
                    to_type = mapping.get("to_type", "params")
                    if from_step_idx is None or to_field is None:
                        continue
                    extraction = {
                        "from_step": from_step_idx,
                        "from_field": from_field,
                        "to_field": to_field,
                        "to_type": to_type,
                        "success": False,
                        "extracted_value": None,
                        "error_msg": None,
                    }
                    from_data = context.get(f"step_{from_step_idx}", {}).get("response")
                    field_val = _get_value_by_path(from_data, from_field)
                    if field_val is not None:
                        extraction["success"] = True
                        extraction["extracted_value"] = str(field_val)[:100] if len(str(field_val)) > 100 else field_val
                        if to_type == "headers":
                            val_str = str(field_val)
                            if to_field.lower() == "authorization" and not val_str.lower().startswith("bearer "):
                                val_str = f"Bearer {val_str}"
                            request_headers[to_field] = val_str
                        elif to_type in ("url_params", "query"):
                            params_query[to_field] = field_val
                        else:
                            params_body[to_field] = field_val
                    else:
                        extraction["error_msg"] = f"无法从步骤{from_step_idx}提取{from_field}"
                    extractions.append(extraction)
                step_data["request_data"] = params_body
                step_data["url_params"] = params_query
                step_data["request_headers"] = request_headers
                step_data["extractions"] = extractions
                # 根据 Content-Type 选择 body 格式：form-urlencoded 用 data=，否则用 json=
                req_headers = dict(request_headers) if request_headers else {}
                ct = (req_headers.get("Content-Type") or req_headers.get("content-type") or "").lower()
                if method != "GET" and params_body:
                    if "Content-Type" not in [k for k in req_headers.keys()]:
                        req_headers["Content-Type"] = "application/json"
                        ct = "application/json"
                    step_data["request_headers"] = req_headers
                use_form = "x-www-form-urlencoded" in ct or "form-urlencoded" in ct
                body_data = None
                if method != "GET" and params_body:
                    if use_form:
                        # form 编码前，将 dict/list 转为 JSON 字符串（如 parm 字段），否则会变成 Python repr 格式
                        body_data = {}
                        for k, v in params_body.items():
                            if isinstance(v, (dict, list)):
                                body_data[k] = json.dumps(v, ensure_ascii=False)
                            elif v is not None:
                                body_data[k] = str(v) if not isinstance(v, str) else v
                            else:
                                body_data[k] = ""
                    else:
                        body_data = params_body
                res = await client.request(
                    method,
                    url,
                    params=params_query if params_query else None,
                    data=body_data if use_form and body_data else None,
                    json=body_data if not use_form and body_data else None,
                    headers=req_headers,
                    timeout=15.0,
                )
                duration = (datetime.now() - start_time).total_seconds()
                res_content = res.text
                try:
                    res_content = res.json()
                except Exception:
                    pass
                full_url = url
                if params_query:
                    full_url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params_query)
                resp_headers = {}
                if hasattr(res, "headers"):
                    try:
                        resp_headers = {k: v for k, v in res.headers.items()}
                    except Exception:
                        pass
                expected_status = step.get("expected_status")
                if expected_status is None:
                    expected_status = 200
                http_passed = res.status_code == expected_status if expected_status is not None else res.status_code < 400
                # 业务断言：校验响应体中的字段（如 code、message），与 HTTP 断言二选一通过即视为成功
                expected_response_body = step.get("expected_response_body") or {}
                business_passed = True
                business_details = []
                if expected_response_body and isinstance(expected_response_body, dict):
                    resp_obj = res_content if isinstance(res_content, dict) else {}
                    if not isinstance(res_content, dict) and isinstance(res_content, str):
                        try:
                            resp_obj = json.loads(res_content) if res_content else {}
                        except Exception:
                            resp_obj = {}
                    
                    # 字段名映射表：支持不同API的字段名变体
                    FIELD_NAME_MAPPING = {
                        "code": ["code", "errcode", "retCode", "status", "ret", "error_code", "statusCode"],
                        "message": ["message", "msg", "errmsg", "info", "error", "desc", "description"],
                        "data": ["data", "result", "content", "body", "list"],
                    }
                    BASIC_CODE_FIELDS = set(FIELD_NAME_MAPPING["code"])
                    MESSAGE_FIELDS = set(FIELD_NAME_MAPPING["message"])

                    def _shorten(val: Any) -> Any:
                        """
                        将 very long 的实际值/期望值做友好截断，避免在前端显示一大串 token / JSON。
                        只在展示用的 business_details 里截断，不影响真实断言逻辑。
                        """
                        try:
                            s = json.dumps(val, ensure_ascii=False)
                        except Exception:
                            s = str(val)
                        # 200 字符足够让人看明白字段值，大于此长度只保留前缀
                        if len(s) > 200:
                            return s[:200] + "…(已截断)"
                        return s
                    
                    for field_path, expected_val in expected_response_body.items():
                        # 提取字段名（支持路径如 "data.code"）
                        path_parts = field_path.split(".")
                        base_field = path_parts[0] if path_parts else field_path
                        
                        # 尝试直接提取
                        actual = _get_value_by_path(resp_obj, field_path)
                        
                        # 如果直接提取失败，尝试字段名映射（仅对顶级字段）
                        if actual is None and len(path_parts) == 1 and base_field in FIELD_NAME_MAPPING:
                            for alt_field in FIELD_NAME_MAPPING[base_field]:
                                if alt_field != base_field and alt_field in resp_obj:
                                    actual = resp_obj[alt_field]
                                    field_path = alt_field  # 更新字段路径用于显示
                                    break
                        
                        # 类型兼容比较：支持字符串和数字的互转比较
                        match = False
                        if expected_val is None:
                            match = actual is not None
                        else:
                            # 严格相等
                            if actual == expected_val:
                                match = True
                            else:
                                # 类型转换后比较（字符串和数字互转）
                                try:
                                    # 尝试将期望值和实际值都转为字符串比较
                                    if str(actual) == str(expected_val):
                                        match = True
                                    # 尝试数字比较
                                    elif isinstance(expected_val, (int, float)) and isinstance(actual, (int, float)):
                                        match = abs(float(actual) - float(expected_val)) < 0.0001
                                    elif isinstance(expected_val, (int, float)) and isinstance(actual, str):
                                        try:
                                            match = float(actual) == float(expected_val)
                                        except (ValueError, TypeError):
                                            pass
                                    elif isinstance(expected_val, str) and isinstance(actual, (int, float)):
                                        try:
                                            match = str(actual) == expected_val or float(actual) == float(expected_val)
                                        except (ValueError, TypeError):
                                            pass
                                except (ValueError, TypeError):
                                    pass

                        # 针对 message 等提示语字段，支持「多候选文案」和包含匹配：
                        # 例如期望值为 "用户不存在或密码错误"，实际返回 "用户不存在" 也视为通过
                        if (
                            not match
                            and isinstance(expected_val, str)
                            and isinstance(actual, str)
                        ):
                            normalized_field_for_msg = field_path.split(".")[-1] if field_path else ""
                            if normalized_field_for_msg in MESSAGE_FIELDS:
                                # 按中文“或”、逗号等拆分成多个候选文案
                                candidates = [c.strip() for c in re.split(r"[，,;/]|或", expected_val) if c.strip()]
                                if not candidates:
                                    candidates = [expected_val.strip()]
                                for cand in candidates:
                                    if cand and (cand in actual or actual in cand):
                                        match = True
                                        break
                        
                        # 断言分类：用于前端按「基础响应 / 业务数据 / 数据完整性」展示
                        # - code 等状态码字段 -> basic
                        # - 期望为空/非空之类 -> integrity
                        # - 其它 -> business_data
                        normalized_field = field_path.split(".")[-1] if field_path else ""
                        category = "business_data"
                        text_expected = str(expected_val).strip() if expected_val is not None else ""
                        if normalized_field in BASIC_CODE_FIELDS:
                            category = "basic"
                        elif (
                            expected_val is None
                            or text_expected in {"非空", "not null", "not_null", "not_empty", "存在", "exists"}
                        ):
                            category = "integrity"

                        business_details.append({
                            "field": field_path,
                            "expected": _shorten(expected_val),
                            "actual": _shorten(actual),
                            "passed": match,
                            "category": category,
                        })
                        if not match:
                            business_passed = False
                else:
                    business_details = []
                # 保留 HTTP 断言；若配置了业务断言且业务断言通过，则即使 HTTP 状态码与期望不符也视为通过（如 200 但 body 中 code=401、message=密码错误）
                success = http_passed or (bool(expected_response_body) and business_passed)
                assertions = [
                    {
                        "type": "http",
                        "category": "basic",
                        "passed": http_passed,
                        "message": f"状态码 {res.status_code} 与期望 {expected_status} {'一致' if http_passed else '不一致'}",
                    },
                ]
                if expected_response_body:
                    assertions.append({
                        "type": "business",
                        "passed": business_passed,
                        "message": "业务字段符合预期" if business_passed else f"业务字段校验未通过: {business_details}",
                        "details": business_details,
                    })
                step_data.update({
                    "status_code": res.status_code,
                    "expected_status": expected_status,
                    "duration": duration,
                    "response": res_content,
                    "response_headers": resp_headers,
                    "response_size": len(res.text) if hasattr(res, "text") else 0,
                    "full_url": full_url,
                    "api_path": step.get("api_path"),
                    "api_method": step.get("api_method", method),
                    "success": success,
                    "assertions": assertions,
                    "http_assertion_passed": http_passed,
                    "business_assertion_passed": business_passed if expected_response_body else None,
                })
                context[f"step_{step_order}"] = json.loads(json.dumps(step_data, default=str))
                step_results.append(step_data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                step_data["error"] = f"{type(e).__name__}: {str(e)}"
                step_results.append(step_data)
    return step_results


@app.get("/api/v1/executions")
async def list_executions(
    project_id: str = "default-project",
    test_case_id: Optional[int] = None,
    limit: int = 10
):
    """获取执行历史记录"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM executions WHERE 1=1"
        params = []
        
        if project_id and project_id != "default-project":
            # 尝试通过 test_case_id 关联项目，或者如果 executions 表有 project_id 则直接过滤
            # 这里的数据库结构可能不一，但我们优先尝试 project_id 过滤
            query += " AND (project_id = ? OR test_case_id IN (SELECT id FROM test_cases WHERE project_id = ?))"
            params.extend([project_id, project_id])

        if test_case_id:
            query += " AND test_case_id = ?"
            params.append(test_case_id)
        
        # executions 表目前可能没有 project_id 列，我们在 init 已经加了迁移
        # 如果是老数据 test_case_id 为 0 的，可能无法按 project_id 过滤
        # 但我们尽量尝试
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "test_case_id": r["test_case_id"],
                "status": r["status"],
                "results": json.loads(r["results"] or "[]"),
                "created_at": r["created_at"]
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/executions")
async def execute_case(req: ExecutionRequest):
    """万能执行引擎：支持场景用例和实时单接口执行"""
    try:
        steps = []
        if req.steps:
            steps = req.steps
        elif req.test_case_id:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_cases WHERE id = ?", (req.test_case_id,))
            case = cursor.fetchone()
            conn.close()
            if not case:
                raise HTTPException(status_code=404, detail="用例不存在")
            steps = json.loads(case["steps"])
            for i, s in enumerate(steps):
                if not s.get("step_order"):
                    s["step_order"] = i + 1
        else:
            raise HTTPException(status_code=400, detail="必须提供 test_case_id 或 steps")

        step_results = await _run_steps(steps, req.base_url)
        final_status = "success" if all(s.get("success", False) for s in step_results) else "failed"
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
                (req.test_case_id or 0, final_status, json.dumps(step_results)),
            )
            exec_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception:
            exec_id = 0
        return {"id": exec_id, "status": final_status, "results": step_results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 导入与列表 (保持原有逻辑) ---

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""

class APIBase(BaseModel):
    name: str
    method: str
    path: str
    description: Optional[str] = ""
    base_url: Optional[str] = ""
    headers: Optional[Any] = {}
    request_body: Optional[Any] = {}
    parameters: Optional[Any] = []
    project_id: Optional[str] = "default-project"

class CurlParseRequest(BaseModel):
    curl: str

class StressTestRequest(BaseModel):
    api_id: int
    test_count: int = 10
    expected_debounce_time: int = 500
    request_interval: int = 100

@app.get("/api/v1/projects")
async def list_projects():
    """获取系统中所有项目信息"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/v1/projects")
async def create_project(project: ProjectBase):
    """创建新项目 (自动生成唯一 ID)"""
    try:
        project_id = str(uuid.uuid4())[:8] # 使用 8 位短 UUID
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
            (project_id, project.name, project.description)
        )
        conn.commit()
        conn.close()
        return {"success": True, "project_id": project_id, "name": project.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目及其关联数据"""
    if project_id == "default-project":
        raise HTTPException(status_code=400, detail="不能删除默认项目")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 删除项目、API、环境、用例、场景等
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        cursor.execute("DELETE FROM project_environments WHERE project_id = ?", (project_id,))
        cursor.execute("DELETE FROM scenarios WHERE project_id = ?", (project_id,))
        cursor.execute("DELETE FROM test_cases WHERE project_id = ?", (project_id,))
        
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _flatten_request_body_from_openapi(request_body: Dict) -> Optional[Dict]:
    """
    从 OpenAPI requestBody 提取扁平的 Body 参数（供执行使用）。
    支持 content.application/json、multipart/form-data、x-www-form-urlencoded。
    保持 example 原始类型：parm 的 example 为 JSON 字符串则存为字符串，不解析成对象。
    """
    if not request_body or not isinstance(request_body, dict):
        return None
    content = request_body.get("content") or request_body.get("Content")
    if not isinstance(content, dict):
        return None
    for _ct_key, mediatype in content.items():
        if not isinstance(mediatype, dict):
            continue
        schema = mediatype.get("schema") or mediatype.get("Schema")
        if not isinstance(schema, dict):
            continue
        props = schema.get("properties") or schema.get("Properties") or {}
        if not isinstance(props, dict) or not props:
            continue
        out = {}
        for k, v in props.items():
            if not isinstance(v, dict):
                continue
            ex = v.get("example") if "example" in v else v.get("default")
            if ex is None:
                ex = ""
            if isinstance(ex, (dict, list)):
                out[k] = json.dumps(ex, ensure_ascii=False)
            else:
                out[k] = ex
        return out if out else None
    return None


@app.post("/api/v1/import/swagger")
async def import_swagger(project_id: str = Form("default-project"), source: str = Form(None), file: UploadFile = File(None)):
    try:
        swagger_data = None
        if source:
            async with httpx.AsyncClient() as client:
                res = await client.get(source)
                swagger_data = res.json()
        elif file:
            content = await file.read()
            # 兼容 BOM 与编码：先按 utf-8-sig 解码再解析 JSON
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig")
            swagger_data = json.loads(content)
        else:
            return {"success": False, "message": "请提供 source（URL）或 file（文件）"}

        if not swagger_data or not isinstance(swagger_data, dict):
            return {"success": False, "message": "无效的 Swagger/OpenAPI 数据"}

        # OpenAPI 3 用 paths，Swagger 2 用 path（此处统一用 paths）
        paths = swagger_data.get("paths") or swagger_data.get("path")
        if not paths:
            return {"success": False, "message": "文档中未找到 paths，请确认是有效的 OpenAPI/Swagger JSON"}
        if not isinstance(paths, dict):
            return {"success": False, "message": f"paths 格式异常，应为对象，当前为 {type(paths).__name__}"}

        apis = []
        servers = swagger_data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, details in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                if not isinstance(details, dict):
                    continue
                params = details.get("parameters", [])
                request_body_raw = details.get("requestBody", {})
                request_body_flat = _flatten_request_body_from_openapi(request_body_raw) if isinstance(request_body_raw, dict) else None
                request_body_to_store = request_body_flat if request_body_flat else (request_body_raw if isinstance(request_body_raw, dict) else {})
                apis.append((
                    path,
                    method.upper(),
                    details.get("summary", ""),
                    details.get("description", ""),
                    base_url,
                    json.dumps(params) if isinstance(params, (list, dict)) else "[]",
                    json.dumps(request_body_to_store, ensure_ascii=False) if isinstance(request_body_to_store, dict) else "{}",
                    project_id,
                ))

        if not apis:
            return {
                "success": False,
                "message": "解析后未得到任何接口（paths 下需包含 get/post/put/delete/patch 之一）",
                "paths_count": len(paths),
            }

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        cursor.executemany("""
            INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, apis)
        conn.commit()
        conn.close()

        return {"success": True, "indexed": len(apis), "total": len(apis), "project_id": project_id}
    except json.JSONDecodeError as e:
        return {"success": False, "message": f"JSON 解析失败: {e.msg}，请检查文件编码与格式"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/v1/apis")
async def create_api(api: APIBase):
    """手动创建接口"""
    try:
        def to_json(val):
            if isinstance(val, (dict, list)): return json.dumps(val)
            return str(val)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api.path, api.method, api.name, api.description, api.base_url,
            to_json(api.parameters), to_json(api.request_body), to_json(api.headers), api.project_id
        ))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/apis/{api_id}")
async def update_api(api_id: int, api: APIBase):
    """更新接口定义"""
    try:
        def to_json(val):
            if isinstance(val, (dict, list)): return json.dumps(val)
            return str(val)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE apis SET 
                path = ?, method = ?, summary = ?, description = ?, 
                base_url = ?, parameters = ?, request_body = ?, headers = ?, project_id = ?
            WHERE id = ?
        """, (
            api.path, api.method, api.name, api.description, api.base_url,
            to_json(api.parameters), to_json(api.request_body), to_json(api.headers), api.project_id,
            api_id
        ))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/apis/{api_id}")
async def delete_api_entry(api_id: int):
    """删除单个接口定义"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/parse/curl")
async def parse_curl_command(req: CurlParseRequest):
    """使用 AI 极速解析 cURL"""
    try:
        system_prompt = "你是一个接口专家。解析 cURL 并返回 JSON：{name(中文名), method, path, base_url, headers, request_body, parameters}。无则返回默认值。"
        result = await ai_client.chat(system_prompt, req.curl)
        if "body" in result and "request_body" not in result:
            result["request_body"] = result["body"]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@app.post("/api/v1/test/stress-test")
async def api_stress_test(req: StressTestRequest):
    """简单的压测分析接口（占位实现）"""
    # 这里可以添加真实的并发测试逻辑，目前返回模拟数据以支持前端 UI 展示
    return {
        "analysis": {
            "has_debounce": False,
            "confidence": 100,
            "reasons": ["目前仅作为功能测试返回值"]
        },
        "stats": {
            "total_requests": req.test_count,
            "successful_requests": req.test_count,
            "avg_duration": 0.05,
            "total_time": req.test_count * 0.1
        },
        "test_results": [
            {
                "request_id": i + 1,
                "success": True,
                "duration": 0.05,
                "status_code": 200,
                "response": {"message": "Success"}
            } for i in range(req.test_count)
        ]
    }

@app.get("/api/v1/apis")
async def list_apis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apis ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return {
        "apis": [
            {
                "id": r["id"],
                "path": r["path"],
                "method": r["method"],
                "name": r["summary"] or r["path"],
                "description": r["description"],
                "base_url": r["base_url"],
                "parameters": json.loads(r["parameters"] or "[]"),
                "request_body": json.loads(r["request_body"] or "{}"),
                "headers": json.loads(r["headers"] or "{}"),
                "project_id": r["project_id"],
                "tags": [],
            }
            for r in rows
        ]
    }


@app.get("/api/v1/api-test-plan")
async def generate_api_test_plan(
    project_id: str = "default-project",
    case_types: Optional[str] = None,
    use_ai: bool = False,
):
    """
    API Planner：基于当前项目已导入的 Swagger / API 列表，
    生成每个接口的正向 / 边界 / 健壮 / 安全部分的测试计划。

    - project_id: 项目 ID（默认 default-project）
    - case_types: 可选，用逗号分隔的用例类型，如 "positive,boundary,robustness,security"
    - use_ai: 为 true 时调用大模型为每个接口生成真实测试用例（边界/健壮/安全等含真实请求体），否则使用规则骨架
    """
    include_types: Optional[List[str]] = None
    if case_types:
        include_types = [t.strip().lower() for t in case_types.split(",") if t.strip()]

    plan = api_planner.generate_plan(
        project_id=project_id,
        include_case_types=include_types,
    )

    if use_ai and plan.get("endpoints"):
        enabled_types = list(include_types) if include_types else ["positive", "boundary", "robustness", "security"]
        for ep in plan["endpoints"]:
            try:
                api_id = ep.get("id")
                endpoint_for_ai = {
                    "path": ep.get("path"),
                    "method": ep.get("method"),
                    "summary": ep.get("summary"),
                    "description": ep.get("description"),
                    "base_url": ep.get("base_url"),
                    "parameters": _get_api_parameters(api_id),
                    "request_body": _get_api_request_body(api_id),
                }
                ai_cases = await ai_generate_cases_for_endpoint(
                    ai_client,
                    endpoint_for_ai,
                    include_types=enabled_types,
                )
                if ai_cases:
                    ep["cases"] = ai_cases
            except Exception as e:
                print(f"AI 生成用例失败 endpoint {ep.get('path')}: {e}")
                # 保留规则生成的 cases，不覆盖
                pass
    return plan


class GenerateAiCaseRequest(BaseModel):
    """单接口 AI 生成用例请求（便于前端按接口选择并展示进度）"""
    project_id: str = "default-project"
    api_id: int
    case_types: Optional[str] = None  # 逗号分隔，如 "positive,boundary,robustness,security"


@app.post("/api/v1/api-test-plan/generate-ai-case")
async def generate_ai_case_for_api(req: GenerateAiCaseRequest):
    """
    为单个接口调用大模型生成测试用例。前端可对选中的接口逐个调用并展示进度。
    """
    include_types: Optional[List[str]] = None
    if req.case_types:
        include_types = [t.strip().lower() for t in req.case_types.split(",") if t.strip()]
    else:
        include_types = ["positive", "boundary", "robustness", "security"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, path, method, summary, description, base_url, parameters, request_body FROM apis WHERE id = ? AND project_id = ?",
        (req.api_id, req.project_id),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="接口不存在或不属于当前项目")

    endpoint_for_ai = {
        "path": row["path"],
        "method": row["method"],
        "summary": row["summary"] or "",
        "description": row["description"] or "",
        "base_url": row["base_url"] or "",
        "parameters": json.loads(row["parameters"] or "[]"),
        "request_body": json.loads(row["request_body"] or "{}"),
    }
    try:
        ai_cases = await ai_generate_cases_for_endpoint(
            ai_client,
            endpoint_for_ai,
            include_types=include_types,
        )
    except Exception as e:
        print(f"AI 生成用例失败 api_id={req.api_id}: {e}")
        raise HTTPException(status_code=500, detail=f"大模型生成失败: {str(e)}")
    return {"api_id": req.api_id, "cases": ai_cases}


def _get_api_parameters(api_id: Optional[int]) -> List[Dict]:
    """从 apis 表读取 parameters（供 use_ai 时补齐 endpoint 信息）"""
    if not api_id:
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT parameters FROM apis WHERE id = ?", (api_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row["parameters"]:
            return json.loads(row["parameters"] or "[]")
    except Exception:
        pass
    return []


def _get_api_request_body(api_id: Optional[int]) -> Dict:
    """从 apis 表读取 request_body（供 use_ai 时补齐 endpoint 信息）"""
    if not api_id:
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT request_body FROM apis WHERE id = ?", (api_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row["request_body"]:
            return json.loads(row["request_body"] or "{}")
    except Exception:
        pass
    return {}


class ExecutePlanRequest(BaseModel):
    """执行 API 测试计划的请求体。传入 plan 时使用前端当前计划（含 AI 用例），否则后端重新生成规则计划"""
    project_id: str = "default-project"
    base_url: str = ""
    case_types: Optional[str] = None  # 逗号分隔，如 "positive,boundary"
    environment: str = "test"
    plan: Optional[Dict[str, Any]] = None  # 前端传入的当前计划（endpoints + cases），有则用其执行


class ExecuteCaseRequest(BaseModel):
    """执行单个用例的请求体（与计划中 endpoint + case 结构一致）"""
    project_id: str = "default-project"
    base_url: str = ""
    environment: str = "test"
    endpoint: Dict[str, Any]  # method, path, base_url?
    case: Dict[str, Any]  # request_template, expected_template, case_type, name?


class ApiTestCaseCreate(BaseModel):
    """为单个接口保存一条用例到用例库"""
    project_id: str = "default-project"
    api_id: Optional[int] = None
    method: str
    path: str
    source: Optional[str] = None  # ai / rule / manual
    case_type: Optional[str] = None
    name: str
    description: Optional[str] = ""
    request_template: Dict[str, Any]
    expected_template: Dict[str, Any]


class ApiTestCaseOut(BaseModel):
    id: int
    project_id: str
    api_id: Optional[int]
    method: str
    path: str
    source: Optional[str]
    case_type: Optional[str]
    name: str
    description: Optional[str]
    request_template: Dict[str, Any]
    expected_template: Dict[str, Any]
    created_at: str
    updated_at: str


@app.post("/api/v1/api-test-plan/execute-case")
async def execute_single_case(req: ExecuteCaseRequest):
    """
    执行单个测试用例：根据传入的 endpoint + case 发一次请求，
    按用例期望状态码判定通过/失败，返回该条结果。
    """
    try:
        base_url = (req.base_url or "").strip()
        if not base_url:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT base_url FROM project_environments WHERE project_id = ? AND (env_name = ? OR is_default = 1) ORDER BY is_default DESC LIMIT 1",
                (req.project_id, req.environment),
            )
            row = cursor.fetchone()
            conn.close()
            base_url = (row["base_url"] or "").strip() if row else ""
        if not base_url:
            raise HTTPException(status_code=400, detail="请提供 base_url 或在项目环境中配置 base_url")

        ep = req.endpoint
        case = req.case
        rt = case.get("request_template") or {}
        et = case.get("expected_template") or {}
        expected_status = et.get("status_code", 200)
        api_path = case.get("path") or ep.get("path") or ""
        api_method = (case.get("method") or ep.get("method") or "GET").upper()

        steps = [{
            "step_order": 1,
            "api_path": api_path,
            "api_method": api_method,
            "params": rt.get("params") or {},
            "url_params": rt.get("url_params") or {},
            "headers": rt.get("headers") or {},
            "param_mappings": [],
            "base_url": (ep.get("base_url") or "").strip() or base_url,
        }]
        step_results = await _run_steps(steps, base_url)
        sr = step_results[0] if step_results else {}
        ct = case.get("case_type", "positive")
        if hasattr(ct, "value"):
            ct = ct.value
        sr["case_type"] = ct
        sr["expected_status"] = expected_status
        sr["success"] = (sr.get("status_code") == expected_status)

        return {"result": sr, "success": sr.get("success")}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/api-test-cases", response_model=ApiTestCaseOut)
async def save_api_test_case(case_in: ApiTestCaseCreate):
    """将当前计划中的某条接口用例保存到 API 级用例库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute(
            """
            INSERT INTO api_test_cases
            (project_id, api_id, method, path, source, case_type, name, description, request_template, expected_template, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_in.project_id,
                case_in.api_id,
                case_in.method,
                case_in.path,
                (case_in.source or "").lower() or None,
                (case_in.case_type or "").lower() or None,
                case_in.name,
                case_in.description or "",
                json.dumps(case_in.request_template or {}, ensure_ascii=False),
                json.dumps(case_in.expected_template or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM api_test_cases WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "api_id": row["api_id"],
            "method": row["method"],
            "path": row["path"],
            "source": row["source"],
            "case_type": row["case_type"],
            "name": row["name"],
            "description": row["description"],
            "request_template": json.loads(row["request_template"] or "{}"),
            "expected_template": json.loads(row["expected_template"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/api-test-cases")
async def list_api_test_cases(project_id: str = "default-project", api_id: Optional[int] = None):
    """列出某项目下（可选按接口）已保存的 API 级测试用例"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if api_id is not None:
            cursor.execute(
                "SELECT * FROM api_test_cases WHERE project_id = ? AND api_id = ? ORDER BY created_at DESC, id DESC",
                (project_id, api_id),
            )
        else:
            cursor.execute(
                "SELECT * FROM api_test_cases WHERE project_id = ? ORDER BY created_at DESC, id DESC",
                (project_id,),
            )
        rows = cursor.fetchall()
        conn.close()
        out = []
        for row in rows:
            try:
                req_tpl = json.loads(row["request_template"] or "{}")
            except Exception:
                req_tpl = {}
            try:
                exp_tpl = json.loads(row["expected_template"] or "{}")
            except Exception:
                exp_tpl = {}
            out.append(
                {
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "api_id": row["api_id"],
                    "method": row["method"],
                    "path": row["path"],
                    "source": row["source"],
                    "case_type": row["case_type"],
                    "name": row["name"],
                    "description": row["description"],
                    "request_template": req_tpl,
                    "expected_template": exp_tpl,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return out
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/api-test-cases/{case_id}")
async def delete_api_test_case(case_id: int):
    """删除已保存的 API 级测试用例"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_test_cases WHERE id = ?", (case_id,))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/api-test-plan/execute")
async def execute_api_test_plan(req: ExecutePlanRequest):
    """
    执行 API 测试计划：根据 project_id 生成计划用例，逐条发请求，
    按用例类型的期望状态码判定通过/失败，并返回汇总报告。
    """
    try:
        base_url = (req.base_url or "").strip()
        if not base_url:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT base_url FROM project_environments WHERE project_id = ? AND (env_name = ? OR is_default = 1) ORDER BY is_default DESC LIMIT 1",
                (req.project_id, req.environment),
            )
            row = cursor.fetchone()
            conn.close()
            base_url = (row["base_url"] or "").strip() if row else ""
        if not base_url:
            raise HTTPException(status_code=400, detail="请提供 base_url 或在项目环境中配置 base_url")

        # 优先使用前端传入的当前计划（含已生成的 AI 用例）
        include_types = None
        if req.case_types:
            include_types = [t.strip().lower() for t in req.case_types.split(",") if t.strip()]
        
        if req.plan and isinstance(req.plan, dict) and (req.plan.get("endpoints") or []):
            endpoints = req.plan.get("endpoints") or []
            # 调试日志：检查传入的 plan 结构
            print(f"DEBUG: 使用前端传入的 plan，endpoints 数量: {len(endpoints)}")
            if include_types:
                print(f"DEBUG: 需要过滤的用例类型: {include_types}")
            for i, ep in enumerate(endpoints):
                cases_count = len(ep.get("cases") or [])
                print(f"DEBUG: endpoint[{i}]: path={ep.get('path')}, method={ep.get('method')}, cases数量={cases_count}")
        else:
            plan = api_planner.generate_plan(project_id=req.project_id, include_case_types=include_types)
            endpoints = plan.get("endpoints") or []
            print(f"DEBUG: 重新生成 plan，endpoints 数量: {len(endpoints)}")
        steps = []
        meta_list = []  # (case_type, expected_status) 与 steps 一一对应
        for ep in endpoints:
            base_url_ep = (ep.get("base_url") or "").strip() or base_url
            ep_path = (ep.get("path") or "").strip()
            ep_method = (ep.get("method") or "GET").upper()
            cases = ep.get("cases") or []
            if not cases:
                print(f"DEBUG: 警告 - endpoint {ep_method} {ep_path} 的 cases 列表为空或不存在")
                continue
            # 如果指定了 case_types，需要过滤用例
            filtered_cases = cases
            if include_types:
                filtered_cases = []
                for case in cases:
                    case_type = (case.get("case_type") or "positive").lower()
                    if case_type in include_types:
                        filtered_cases.append(case)
                    else:
                        print(f"DEBUG: 过滤掉用例 - case_type={case_type}, name={case.get('name', '')}")
                if len(filtered_cases) < len(cases):
                    print(f"DEBUG: endpoint {ep_method} {ep_path} 过滤后用例数量: {len(filtered_cases)}/{len(cases)}")
            for case in filtered_cases:
                rt = case.get("request_template") or {}
                et = case.get("expected_template") or {}
                expected_status = et.get("status_code", 200)
                # AI 生成的 case 可能没有 path/method，必须从 endpoint 回退，否则请求地址会变成 base_url/ 且无 path
                case_path = (case.get("path") or "").strip() or ep_path
                case_method = (case.get("method") or "").upper() or ep_method
                steps.append({
                    "step_order": len(steps) + 1,
                    "api_path": case_path,
                    "api_method": case_method,
                    "params": rt.get("params") or {},
                    "url_params": rt.get("url_params") or {},
                    "headers": rt.get("headers") or {},
                    "param_mappings": [],
                    "base_url": base_url_ep,
                    "expected_status": expected_status,
                    "expected_response_body": et.get("response_body") or et.get("expected_response") or {},
                })
                ct = case.get("case_type", "positive")
                if hasattr(ct, "value"):
                    ct = ct.value
                meta_list.append((ct, expected_status))

        if not steps:
            # 提供更详细的错误信息，帮助诊断问题
            total_endpoints = len(endpoints)
            endpoints_with_cases = sum(1 for ep in endpoints if ep.get("cases"))
            total_cases = sum(len(ep.get("cases") or []) for ep in endpoints)
            error_detail = (
                f"未找到可执行的用例。"
                f"统计信息：接口数量={total_endpoints}，"
                f"有用例的接口数量={endpoints_with_cases}，"
                f"用例总数={total_cases}。"
                f"请确保已生成测试用例（点击「AI生成用例」按钮），"
                f"或检查传入的 plan 数据中 endpoints[].cases 是否包含有效的用例。"
            )
            print(f"DEBUG: {error_detail}")
            raise HTTPException(status_code=400, detail=error_detail)

        step_results = await _run_steps(steps, base_url)
        for i, sr in enumerate(step_results):
            if i < len(meta_list):
                case_type, expected_status = meta_list[i]
                sr["case_type"] = case_type
                sr["expected_status"] = expected_status
                # 不覆盖 success：_run_steps 已按 HTTP 断言 + 业务断言（expected_response_body）计算，保留其结果

        passed = sum(1 for s in step_results if s.get("success"))
        failed = len(step_results) - passed
        by_case_type = {}
        for s in step_results:
            ct = s.get("case_type", "unknown")
            if ct not in by_case_type:
                by_case_type[ct] = {"total": 0, "passed": 0, "failed": 0}
            by_case_type[ct]["total"] += 1
            if s.get("success"):
                by_case_type[ct]["passed"] += 1
            else:
                by_case_type[ct]["failed"] += 1

        final_status = "success" if failed == 0 else "failed"
        exec_id = 0
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO executions (test_case_id, status, results, project_id) VALUES (?, ?, ?, ?)",
                    (0, final_status, json.dumps(step_results), req.project_id),
                )
            except sqlite3.OperationalError:
                cursor.execute(
                    "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
                    (0, final_status, json.dumps(step_results)),
                )
            exec_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "id": exec_id,
            "status": final_status,
            "project_id": req.project_id,
            "summary": {
                "total": len(step_results),
                "passed": passed,
                "failed": failed,
                "by_case_type": by_case_type,
            },
            "results": step_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/executions/{execution_id}")
async def get_execution(execution_id: int):
    """根据执行 id 查询单次执行记录（含结果与各步详情）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, test_case_id, status, results, created_at FROM executions WHERE id = ?", (execution_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    results = []
    try:
        results = json.loads(row["results"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "test_case_id": row["test_case_id"],
        "status": row["status"],
        "results": results,
        "created_at": row["created_at"],
    }


# ============= 测试报告总览接口 =============

def _parse_time_range(time_range: str) -> str:
    """返回 SQLite 日期表达式，如 -7 days"""
    if time_range == "90d":
        return "-90 days"
    if time_range == "30d":
        return "-30 days"
    return "-7 days"


# ============= 接口测试报告 CRUD =============

class TestReportCreate(BaseModel):
    project_id: str = "default-project"
    name: str
    report_type: Optional[str] = "接口测试"
    creator: Optional[str] = ""
    trigger_method: Optional[str] = "手动触发"
    status: str = "success"
    payload: Dict[str, Any]


@app.post("/api/v1/test-reports")
async def create_test_report(req: TestReportCreate):
    """保存接口测试执行报告"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """INSERT INTO test_reports (project_id, name, report_type, creator, created_at, end_time, trigger_method, status, payload)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (req.project_id, req.name, req.report_type or "接口测试", req.creator or "", now, now, req.trigger_method or "手动触发", req.status, json.dumps(req.payload, ensure_ascii=False, default=str)),
    )
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": report_id, "name": req.name, "created_at": now}


@app.get("/api/v1/test-reports")
async def list_test_reports(project_id: str = "default-project"):
    """获取项目下所有测试报告列表"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, project_id, name, report_type, creator, created_at, end_time, trigger_method, status FROM test_reports WHERE project_id = ? ORDER BY created_at DESC",
        (project_id or "default-project",),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/v1/test-reports/{report_id}")
async def get_test_report(report_id: int):
    """获取报告详情"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")
    d = dict(row)
    if d.get("payload"):
        try:
            d["payload"] = json.loads(d["payload"])
        except Exception:
            d["payload"] = {}
    return d


class TestReportUpdate(BaseModel):
    name: str


@app.put("/api/v1/test-reports/{report_id}")
async def update_test_report(report_id: int, req: TestReportUpdate):
    """更新报告名称"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE test_reports SET name = ? WHERE id = ?", (req.name, report_id))
    conn.commit()
    updated = cursor.rowcount
    conn.close()
    if updated == 0:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"success": True}


@app.delete("/api/v1/test-reports/{report_id}")
async def delete_test_report(report_id: int):
    """删除报告"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM test_reports WHERE id = ?", (report_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"success": True}


@app.get("/api/v1/reports/overview")
async def reports_overview(project_id: str = "default-project", time_range: str = "7d"):
    """总执行次数、成功/失败、成功率、平均响应时间、场景数"""
    days = _parse_time_range(time_range)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        proj = project_id or "default-project"
        cursor.execute(
            """SELECT id, status, results FROM executions
               WHERE created_at >= datetime('now', ?)
               AND (project_id = ? OR (project_id IS NULL AND ? = 'default-project'))""",
            (days, proj, proj),
        )
    except sqlite3.OperationalError:
        cursor.execute(
            "SELECT id, status, results FROM executions WHERE created_at >= datetime('now', ?)",
            (days,),
        )
    rows = cursor.fetchall()
    conn.close()

    total_executions = len(rows)
    success_count = sum(1 for r in rows if (r["status"] or "").lower() == "success")
    failed_count = total_executions - success_count
    success_rate = (success_count / total_executions) if total_executions else 0.0

    total_duration = 0.0
    step_count = 0
    for r in rows:
        try:
            results = json.loads(r["results"] or "[]")
            for s in results:
                d = s.get("duration")
                if d is not None and isinstance(d, (int, float)):
                    total_duration += float(d)
                    step_count += 1
        except Exception:
            pass
    avg_response_time = round(total_duration / step_count * 1000, 0) if step_count else 0

    cursor = sqlite3.connect(DB_PATH).cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM test_cases WHERE project_id = ?", (project_id,))
        total_scenarios = cursor.fetchone()[0] or 0
    except Exception:
        total_scenarios = 0
    try:
        cursor.execute(
            """SELECT COUNT(DISTINCT test_case_id) FROM executions
               WHERE test_case_id > 0 AND created_at >= datetime('now', ?)""",
            (days,),
        )
        active_scenarios = cursor.fetchone()[0] or 0
    except Exception:
        active_scenarios = 0

    return {
        "total_executions": total_executions,
        "success_count": success_count,
        "failed_count": failed_count,
        "success_rate": success_rate,
        "avg_response_time": int(avg_response_time),
        "total_scenarios": total_scenarios,
        "active_scenarios": active_scenarios,
    }


@app.get("/api/v1/reports/trends")
async def reports_trends(project_id: str = "default-project", metric: str = "success_rate", days: int = 30):
    """成功率趋势：按日聚合"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        proj = project_id or "default-project"
        cursor.execute(
            """SELECT date(created_at) as d, status FROM executions
               WHERE created_at >= datetime('now', ?)
               AND (project_id = ? OR (project_id IS NULL AND ? = 'default-project'))""",
            (f"-{days} days", proj, proj),
        )
    except sqlite3.OperationalError:
        cursor.execute(
            "SELECT date(created_at) as d, status FROM executions WHERE created_at >= datetime('now', ?)",
            (f"-{days} days",),
        )
    rows = cursor.fetchall()
    conn.close()

    by_date: Dict[str, List[str]] = {}
    for r in rows:
        d = r["d"] or ""
        if d not in by_date:
            by_date[d] = []
        by_date[d].append((r["status"] or "").lower())
    out = []
    for d in sorted(by_date.keys()):
        vals = by_date[d]
        total = len(vals)
        success = sum(1 for v in vals if v == "success")
        out.append({"date": d, "value": success / total if total else 0})
    return out


@app.get("/api/v1/reports/api-stats")
async def reports_api_stats(project_id: str = "default-project", time_range: str = "7d"):
    """接口统计 Top 20：按 url 聚合请求次数、涉及执行数、成功、失败、成功率（与总览时间范围一致）"""
    days = _parse_time_range(time_range)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        proj = project_id or "default-project"
        cursor.execute(
            """SELECT id, results FROM executions
               WHERE created_at >= datetime('now', ?)
               AND (project_id = ? OR (project_id IS NULL AND ? = 'default-project'))""",
            (days, proj, proj),
        )
    except sqlite3.OperationalError:
        cursor.execute(
            "SELECT id, results FROM executions WHERE created_at >= datetime('now', ?)",
            (days,),
        )
    rows = cursor.fetchall()
    conn.close()

    agg: Dict[str, Dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        exec_id = row[0] if len(row) > 1 else idx
        try:
            results = json.loads((row[1] if len(row) > 1 else row[0]) or "[]")
            for s in results:
                url = s.get("url") or s.get("api_path") or ""
                method = (s.get("method") or "GET").upper()
                key = f"{method} {url}"
                if key not in agg:
                    agg[key] = {
                        "api_name": key,
                        "request_count": 0,
                        "run_count": set(),
                        "success_count": 0,
                        "failed_count": 0,
                    }
                agg[key]["request_count"] += 1
                agg[key]["run_count"].add(exec_id)
                if s.get("success"):
                    agg[key]["success_count"] += 1
                else:
                    agg[key]["failed_count"] += 1
        except Exception:
            pass
    list_out = []
    for v in agg.values():
        run_count = len(v["run_count"])
        v.pop("run_count", None)
        v["run_count"] = run_count
        t = v["request_count"]
        v["success_rate"] = (v["success_count"] / t) if t else 0
        list_out.append(v)
    list_out.sort(key=lambda x: -x["request_count"])
    return list_out[:20]


@app.get("/api/v1/reports/failures")
async def reports_failures(project_id: str = "default-project", days: int = 7):
    """失败分类：按状态码或错误类型聚合"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        proj = project_id or "default-project"
        cursor.execute(
            """SELECT results FROM executions
               WHERE created_at >= datetime('now', ?)
               AND (project_id = ? OR (project_id IS NULL AND ? = 'default-project'))""",
            (f"-{days} days", proj, proj),
        )
    except sqlite3.OperationalError:
        cursor.execute(
            "SELECT results FROM executions WHERE created_at >= datetime('now', ?)",
            (f"-{days} days",),
        )
    rows = cursor.fetchall()
    conn.close()

    by_category: Dict[str, int] = {}
    for row in rows:
        try:
            results = json.loads(row[0] or "[]")
            for s in results:
                if s.get("success"):
                    continue
                code = s.get("status_code")
                if code is not None:
                    c = int(code)
                    if 400 <= c < 500:
                        cat = "4xx 客户端错误"
                    elif 500 <= c < 600:
                        cat = "5xx 服务端错误"
                    elif 200 <= c < 300:
                        cat = "断言失败(实际2xx)"
                    else:
                        cat = f"HTTP {code}"
                else:
                    cat = "异常/超时"
                by_category[cat] = by_category.get(cat, 0) + 1
        except Exception:
            pass
    failure_categories = [{"category": k, "count": v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])]
    return {"failure_categories": failure_categories}


def _normalize_results_to_steps(results: List[Dict]) -> List[Dict]:
    """将 executions.results 转为 Healer 期望的 steps 格式"""
    steps = []
    for r in results:
        steps.append({
            "step_order": r.get("step_order"),
            "api_method": r.get("method"),
            "api_path": r.get("url"),  # 完整 URL，便于 AI 分析
            "url": r.get("url"),
            "params": r.get("request_data") or r.get("params") or {},
            "request_data": r.get("request_data"),
            "request_headers": r.get("request_headers") or r.get("headers") or {},
            "headers": r.get("request_headers") or {},
            "status_code": r.get("status_code"),
            "error_msg": r.get("error"),
            "error": r.get("error"),
            "response": r.get("response"),
            "success": r.get("success"),
            "expected_status": r.get("expected_status"),
            "case_type": r.get("case_type"),
            "assertions": r.get("assertions", []),
        })
    return steps


# ============= API Healer：失败用例分析与自愈 =============

class HealAnalyzeRequest(BaseModel):
    """失败分析请求"""
    execution_id: int
    step_index: Optional[int] = None  # 只分析第几步，不传则分析所有失败步


class HealApplyRequest(BaseModel):
    """应用修复请求（仅场景用例 test_case_id > 0）"""
    test_case_id: int
    execution_id: Optional[int] = None  # 不传则需在下次执行后单独传 execution_result


@app.get("/api/v1/projects/{project_id}/export")
async def export_project(project_id: str):
    """导出项目及其所有关联数据（API、环境、场景、用例）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 项目基本信息
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = dict(cursor.fetchone() or {})
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
            
        # 2. 接口列表
        cursor.execute("SELECT * FROM apis WHERE project_id = ?", (project_id,))
        apis = [dict(row) for row in cursor.fetchall()]
        
        # 3. 环境配置
        cursor.execute("SELECT * FROM project_environments WHERE project_id = ?", (project_id,))
        environments = [dict(row) for row in cursor.fetchall()]
        
        # 4. 场景
        cursor.execute("SELECT * FROM scenarios WHERE project_id = ?", (project_id,))
        scenarios = [dict(row) for row in cursor.fetchall()]
        
        # 5. 场景测试用例
        cursor.execute("SELECT * FROM test_cases WHERE project_id = ?", (project_id,))
        test_cases = [dict(row) for row in cursor.fetchall()]

        # 6. API 级测试用例
        cursor.execute("SELECT * FROM api_test_cases WHERE project_id = ?", (project_id,))
        api_test_cases = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        export_data = {
            "version": "1.0",
            "project": project,
            "apis": apis,
            "environments": environments,
            "scenarios": scenarios,
            "test_cases": test_cases,
            "api_test_cases": api_test_cases
        }
        
        return export_data
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/projects/import")
async def import_project(data: Dict[str, Any]):
    """导入项目数据"""
    try:
        project = data.get("project")
        if not project or not project.get("id"):
            raise HTTPException(status_code=400, detail="无效的项目数据")
            
        project_id = project["id"]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查项目是否已存在
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if cursor.fetchone():
            import uuid
            project_id = f"{project_id}_imported_{uuid.uuid4().hex[:4]}"
            project["id"] = project_id
            project["name"] = f"{project['name']} (导入)"

        # 插入项目信息
        cursor.execute(
            "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (project["id"], project["name"], project.get("description", ""), project.get("created_at"))
        )
        
        def safe_json_dump(val):
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return val

        # 2. 接口列表
        for item in data.get("apis", []):
            cursor.execute(
                """INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item["path"], item["method"], item.get("summary"), item.get("description"), item.get("base_url"),
                 safe_json_dump(item.get("parameters")), safe_json_dump(item.get("request_body")), 
                 safe_json_dump(item.get("headers")), project_id, item.get("created_at"))
            )
            
        # 3. 环境配置
        for item in data.get("environments", []):
            cursor.execute(
                "INSERT INTO project_environments (project_id, env_name, base_url, is_default, created_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, item["env_name"], item["base_url"], item.get("is_default", 0), item.get("created_at"))
            )
            
        # 4. 场景
        for item in data.get("scenarios", []):
            cursor.execute(
                """INSERT INTO scenarios (name, description, natural_language_input, project_id, nlu_result, test_case_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (item.get("name"), item.get("description"), item.get("natural_language_input"), project_id,
                 safe_json_dump(item.get("nlu_result")), item.get("test_case_id"), item.get("created_at"))
            )
            
        # 5. 场景测试用例
        for item in data.get("test_cases", []):
            cursor.execute(
                "INSERT INTO test_cases (name, steps, project_id, created_at) VALUES (?, ?, ?, ?)",
                (item.get("name"), safe_json_dump(item.get("steps")), project_id, item.get("created_at"))
            )

        # 6. API 级测试用例
        for item in data.get("api_test_cases", []):
            cursor.execute(
                """INSERT INTO api_test_cases (project_id, api_id, method, path, source, case_type, name, description, request_template, expected_template, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (project_id, item.get("api_id"), item.get("method"), item.get("path"), item.get("source"),
                 item.get("case_type"), item.get("name"), item.get("description"),
                 safe_json_dump(item.get("request_template")), safe_json_dump(item.get("expected_template")),
                 item.get("created_at"), item.get("updated_at"))
            )
            
        conn.commit()
        conn.close()
        return {"success": True, "project_id": project_id, "message": f"项目 {project['name']} 已成功导入"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/heal/analyze")
async def heal_analyze(req: HealAnalyzeRequest):
    """
    API Healer - 分析失败原因：根据某次执行记录，对失败步骤做根因分析并给出修复建议。
    返回：失败类型、根因、是否可自愈、修复建议（含 patch_hint）。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, test_case_id, status, results FROM executions WHERE id = ?", (req.execution_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="执行记录不存在")
        results = []
        try:
            results = json.loads(row["results"] or "[]")
        except Exception:
            pass
        steps = _normalize_results_to_steps(results)
        failed_steps = [s for s in steps if s.get("success") is False]
        if req.step_index is not None:
            idx = req.step_index
            if idx < 0 or idx >= len(steps):
                raise HTTPException(status_code=400, detail="step_index 越界")
            if steps[idx].get("success") is True:
                return {"status": "no_failure", "message": "该步骤已通过", "step_index": idx}
            failed_steps = [steps[idx]]
        if not failed_steps:
            return {"status": "no_failure", "message": "无失败步骤"}
        execution_result = {"steps": failed_steps}
        analysis = await healer_agent.analyze_failure(execution_result)
        analysis["execution_id"] = req.execution_id
        if req.step_index is not None:
            analysis["step_index"] = req.step_index
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/heal/apply")
async def heal_apply(req: HealApplyRequest):
    """
    API Healer - 应用修复：根据某次执行记录的分析结果，自动修改场景用例（test_cases 表）的步骤。
    仅对 test_case_id > 0 的场景用例生效；计划执行（test_case_id=0）无对应用例可改，请用 analyze 查看建议后人工调整。
    """
    if req.test_case_id <= 0:
        raise HTTPException(status_code=400, detail="仅支持对场景用例（test_case_id > 0）应用修复")
    try:
        execution_result = None
        if req.execution_id:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT results FROM executions WHERE id = ?", (req.execution_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                raise HTTPException(status_code=404, detail="执行记录不存在")
            try:
                results = json.loads(row["results"] or "[]")
            except Exception:
                results = []
            execution_result = {"steps": _normalize_results_to_steps(results)}
        if not execution_result or not execution_result.get("steps"):
            raise HTTPException(status_code=400, detail="请提供 execution_id 以指定用于修复的执行记录")
        result = await healer_agent.heal(req.test_case_id, execution_result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============= 定时任务调度服务 =============

from services.scheduler_service import SchedulerService

# 初始化调度服务
scheduler_service = SchedulerService(DB_PATH)

class ScheduledJobCreateRequest(BaseModel):
    name: str
    description: str = ""
    project_id: str
    scenario_id: int
    cron: str
    environment_id: Optional[int] = None
    notification_config: str = "{}"
    is_active: bool = True

@app.post("/api/v1/scheduler/jobs")
async def create_scheduled_job(req: ScheduledJobCreateRequest):
    """创建定时任务"""
    try:
        result = await scheduler_service.create_job({
            "name": req.name,
            "description": req.description,
            "project_id": req.project_id,
            "scenario_id": req.scenario_id,
            "cron": req.cron,
            "environment_id": req.environment_id,
            "notification_config": req.notification_config
        })
        return result
    except Exception as e:
        print(f"❌ 创建定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/scheduler/jobs/{job_id}")
async def update_scheduled_job(job_id: int, req: ScheduledJobCreateRequest):
    """更新定时任务"""
    try:
        result = await scheduler_service.update_job(job_id, {
            "name": req.name,
            "description": req.description,
            "project_id": req.project_id,
            "scenario_id": req.scenario_id,
            "cron": req.cron,
            "environment_id": req.environment_id,
            "notification_config": req.notification_config
        })
        return result
    except Exception as e:
        print(f"❌ 更新定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scheduler/jobs")
async def get_scheduled_jobs(project_id: str):
    """获取项目的定时任务列表"""
    try:
        jobs = await scheduler_service.get_job_list(project_id)
        return jobs
    except Exception as e:
        print(f"❌ 获取定时任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/scheduler/jobs/{job_id}/pause")
async def pause_scheduled_job(job_id: int):
    """暂停定时任务"""
    try:
        result = await scheduler_service.pause_job(job_id)
        return result
    except Exception as e:
        print(f"❌ 暂停定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/scheduler/jobs/{job_id}/resume")
async def resume_scheduled_job(job_id: int):
    """恢复定时任务"""
    try:
        result = await scheduler_service.resume_job(job_id)
        return result
    except Exception as e:
        print(f"❌ 恢复定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/scheduler/jobs/{job_id}")
async def delete_scheduled_job(job_id: int):
    """删除定时任务"""
    try:
        result = await scheduler_service.delete_job(job_id)
        return result
    except Exception as e:
        print(f"❌ 删除定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/scheduler/jobs/{job_id}/trigger")
async def trigger_scheduled_job(job_id: int):
    """立即执行定时任务"""
    try:
        await scheduler_service.execute_job(job_id)
        return {"message": "任务已触发执行"}
    except Exception as e:
        print(f"❌ 触发定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/scheduler/jobs/{job_id}/history")
async def get_job_history(job_id: int, limit: int = 50):
    """获取任务执行历史"""
    try:
        history = await scheduler_service.get_job_history(job_id, limit)
        return history
    except Exception as e:
        print(f"❌ 获取任务历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 启动时加载所有活跃任务
@app.on_event("startup")
async def startup_event():
    """应用启动时加载定时任务"""
    try:
        # 先启动调度器
        scheduler_service.start()
        # 再加载任务
        await scheduler_service.load_jobs_from_db()
    except Exception as e:
        print(f"⚠️ 加载定时任务失败: {e}")


if __name__ == "__main__":
    print(f"🚀 启动统一后端 (Unified Backend)... 数据库: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
