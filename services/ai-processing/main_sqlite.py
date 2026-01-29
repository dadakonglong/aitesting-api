from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
import sqlite3
import os
import httpx
import urllib.parse
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import uuid
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="AI Testing API - Unified Edition")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
BASE_DIR = "D:/testc/aitesting-api"
DB_PATH = os.path.join(BASE_DIR, "data/apis.db")

# ============= 模型适配层 =============

from openai import AsyncOpenAI

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
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ AI 调用异常: {str(e)}")
            raise Exception(f"AI 服务不可用: {str(e)}")

ai_client = AIProvider()

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
    
    # 测试用例表 (步骤序列)
    cursor.execute('''CREATE TABLE IF NOT EXISTS test_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        steps TEXT, -- JSON 存储步骤
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 执行记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_case_id INTEGER,
        status TEXT, -- success, fail, running
        results TEXT, -- JSON 存储各步详情
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
            if not case: raise HTTPException(status_code=404, detail="用例不存在")
            steps = json.loads(case["steps"])
            print(f"DEBUG: Loaded {len(steps)} steps from test_case {req.test_case_id}")
            # 自动补齐 step_order (防止 context 冲突)
            for i, s in enumerate(steps):
                if not s.get("step_order"): s["step_order"] = i + 1
        else:
            raise HTTPException(status_code=400, detail="必须提供 test_case_id 或 steps")

        context = {} 
        step_results = []
        
        def get_value_by_path(data, path):
            """支持 a.b.c 路径提取"""
            if data is None or not path: return None
            parts = path.split('.')
            curr = data
            for p in parts:
                if isinstance(curr, dict) and p in curr: curr = curr[p]
                elif isinstance(curr, list) and p.isdigit(): # 支持数组索引
                    idx = int(p)
                    if idx < len(curr): curr = curr[idx]
                    else: return None
                else: return None
            return curr

        async with httpx.AsyncClient(verify=False) as client:
            for i, step in enumerate(steps):
                step_order = step.get("step_order", i + 1)
                print(f"DEBUG: Starting step {step_order} [{step.get('api_method', 'GET')} {step.get('api_path')}]")
                start_time = datetime.now()
                
                # 确定 Base URL
                current_base_url = req.base_url.strip() if req.base_url else ""
                if not current_base_url or current_base_url == "http://localhost:8000":
                    current_base_url = (step.get("base_url") or "").strip()
                if not current_base_url:
                    current_base_url = "http://localhost:8000"

                step_data = {
                    "step_order": step_order,
                    "url": "",
                    "method": step.get("api_method", step.get("method", "GET")).upper(),
                    "request_data": step.get("params", {}),
                    "request_headers": step.get("headers", {}).copy(),
                    "success": False,
                    "status_code": "Error"
                }
                
                try:
                    api_path = step.get('api_path', step.get('path', ''))
                    safe_path = urllib.parse.quote(api_path.lstrip('/'), safe="/?=&")
                    url = f"{current_base_url.rstrip('/')}/{safe_path}"
                    step_data["url"] = url
                    
                    params_body = (step.get("params") or {}).copy()
                    params_query = (step.get("url_params") or {}).copy()
                    request_headers = (step.get("headers") or {}).copy()
                    method = step_data["method"]
                    
                    # 记录提取过程
                    extractions = []
                    
                    # 深度依赖映射处理
                    for mapping in step.get("param_mappings", []):
                        from_step_idx = mapping.get("from_step")
                        from_field = mapping.get("from_field")
                        to_field = mapping.get("to_field")
                        to_type = mapping.get("to_type", "params") 
                        
                        if from_step_idx is None or to_field is None: continue
                        
                        # 创建提取记录
                        extraction = {
                            "from_step": from_step_idx,
                            "from_field": from_field,
                            "to_field": to_field,
                            "to_type": to_type,
                            "success": False,
                            "extracted_value": None,
                            "error_msg": None
                        }
                        
                        search_key = f"step_{from_step_idx}"
                        from_data = context.get(search_key, {}).get("response")
                        field_val = get_value_by_path(from_data, from_field)
                        
                        # 调试日志
                        print(f"DEBUG: Extracting from step {from_step_idx}")
                        print(f"DEBUG: from_field = {from_field}")
                        print(f"DEBUG: extracted value = {str(field_val)[:50] if field_val else 'None'}...")
                        
                        if field_val is not None:
                            extraction["success"] = True
                            extraction["extracted_value"] = str(field_val)[:100] if len(str(field_val)) > 100 else field_val
                            
                            if to_type == "headers": 
                                val_str = str(field_val)
                                if to_field.lower() == "authorization" and not val_str.lower().startswith("bearer "):
                                    val_str = f"Bearer {val_str}"
                                request_headers[to_field] = val_str
                                print(f"DEBUG: Set header {to_field} = {val_str[:50]}...")
                            elif to_type == "url_params" or to_type == "query": 
                                params_query[to_field] = field_val
                            else: 
                                params_body[to_field] = field_val
                        else:
                            extraction["error_msg"] = f"无法从步骤{from_step_idx}提取{from_field}"
                            print(f"DEBUG: WARNING - Could not extract {from_field} from step {from_step_idx}")
                        
                        extractions.append(extraction)

                    step_data["request_data"] = params_body
                    step_data["url_params"] = params_query
                    step_data["request_headers"] = request_headers
                    step_data["extractions"] = extractions  # 添加提取记录
                    
                    # 2. 发送请求
                    res = await client.request(
                        method, 
                        url, 
                        params=params_query if params_query else None, 
                        json=params_body if method != "GET" and params_body else None, 
                        headers=request_headers,
                        timeout=15.0
                    )
                    duration = (datetime.now() - start_time).total_seconds()
                    print(f"DEBUG: Step {step_order} response status: {res.status_code}")
                    
                    res_content = res.text
                    try: res_content = res.json()
                    except: pass
                    
                    # 关键修复：深拷贝一份数据放入 context，防止后续引用修改
                    step_data.update({
                        "status_code": res.status_code,
                        "duration": duration,
                        "response": res_content,
                        "success": res.status_code < 400
                    })
                    
                    # 调试日志
                    print(f"DEBUG: Saving step {step_order} to context")
                    if isinstance(res_content, dict) and 'data' in res_content:
                        if 'token' in res_content.get('data', {}):
                            token_val = res_content['data']['token']
                            print(f"DEBUG: Response contains token: {str(token_val)[:30]}...")
                    
                    context[f"step_{step_order}"] = json.loads(json.dumps(step_data, default=str)) 
                    step_results.append(step_data)
                except Exception as e:
                    import traceback
                    print(f"CRITICAL ERROR in Step {step_order}:")
                    traceback.print_exc()
                    step_data["error"] = f"{type(e).__name__}: {str(e)}"
                    step_results.append(step_data)

        # 4. 保存执行记录
        final_status = "success" if all(s.get("success", False) for s in step_results) else "failed"
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
                (req.test_case_id or 0, final_status, json.dumps(step_results))
            )
            exec_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except:
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
            swagger_data = json.loads(content)
        
        if not swagger_data: return {"success": False, "message": "无数据"}
        
        apis = []
        paths = swagger_data.get("paths", {})
        
        # 提取域名 (Base URL)
        servers = swagger_data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    # 提取参数
                    params = details.get("parameters", [])
                    # 提取请求体
                    request_body = details.get("requestBody", {})
                    
                    apis.append((
                        path, 
                        method.upper(), 
                        details.get("summary", ""), 
                        details.get("description", ""), 
                        base_url,
                        json.dumps(params),
                        json.dumps(request_body),
                        project_id
                    ))
        
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
    return {"apis": [
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
            "tags": []
        } for r in rows
    ]}

if __name__ == "__main__":
    print(f"🚀 启动统一后端 (Unified Backend)... 数据库: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
