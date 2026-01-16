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
        project_id TEXT DEFAULT 'default-project',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 自动迁移旧库：增加缺失的列
    try:
        cursor.execute("ALTER TABLE apis ADD COLUMN base_url TEXT")
        cursor.execute("ALTER TABLE apis ADD COLUMN parameters TEXT")
        cursor.execute("ALTER TABLE apis ADD COLUMN request_body TEXT")
    except:
        pass # 列已存在
    
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
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. 获取场景信息
        cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
        scenario = cursor.fetchone()
        if not scenario: raise HTTPException(status_code=404, detail="场景不存在")
        
        # 2. RAG: 简易语义检索 (包含完整参数和请求体以供 AI 精准识别)
        cursor.execute("""
            SELECT path, method, summary, description, base_url, parameters, request_body 
            FROM apis 
            WHERE project_id = ?
        """, (scenario["project_id"],))
        rows_apis = cursor.fetchall()
        all_apis = [dict(row) for row in rows_apis]
        
        # 3. AI 编排
        system_prompt = """你是一个高级接口自动化专家。
        任务：根据给出的【业务意图】和【可用 API 列表】，自动识别出正确的调用链，并以 JSON 格式返回。
        要求：
        1. 识别参数依赖（如 A 接口返回的 id 是 B 接口的输入）。
        2. 生成真实的测试数据（如果是查询，使用典型值；如果是创建，使用随机但合理的姓名/手机号等）。
        3. 自动生成逻辑断言。
        请务必返回合法的 JSON 对象。
        格式：{ "scenario_name": "名称", "steps": [{ "step_order": 1, "api_path": "/path", "api_method": "POST", "description": "...", "params": {}, "headers": {}, "assertions": [], "param_mappings": [] }] }"""
        
        user_prompt = f"意图: {scenario['nlu_result']}\n可用 API: {json.dumps(all_apis[:50])}" # 限制上下文
        case_result = await ai_client.chat(system_prompt, user_prompt)
        
        # 4. 保存测试用例
        cursor.execute(
            "INSERT INTO test_cases (name, steps, project_id) VALUES (?, ?, ?)",
            (case_result.get("scenario_name"), json.dumps(case_result.get("steps")), scenario["project_id"])
        )
        case_id = cursor.lastrowid
        
        # 关联场景
        cursor.execute("UPDATE scenarios SET test_case_id = ? WHERE id = ?", (case_id, scenario_id))
        
        conn.commit()
        conn.close()
        # 兼容前端字段名
        case_result["name"] = case_result.get("scenario_name")
        return case_result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 执行引擎 ---

class ExecutionRequest(BaseModel):
    test_case_id: Optional[int] = None  # 可选,用于完整场景执行
    environment: str = "test"
    base_url: str = "http://localhost:8000"
    steps: Optional[List[Dict]] = None  # 可选,用于单步执行

@app.post("/api/v1/executions")
async def execute_case(req: ExecutionRequest):
    """链式执行引擎：支持变量动态映射和 HTTP 发送"""
    try:
        # 如果直接提供了steps,则使用它(单步执行)
        if req.steps:
            steps = req.steps
        else:
            # 否则从数据库读取(完整场景执行)
            if not req.test_case_id:
                raise HTTPException(status_code=400, detail="必须提供 test_case_id 或 steps")
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM test_cases WHERE id = ?", (req.test_case_id,))
            case = cursor.fetchone()
            if not case: 
                conn.close()
                raise HTTPException(status_code=404, detail="用例不存在")
            
            steps = json.loads(case["steps"])
            conn.close()
        
        context = {} # 存储运行时变量，如 {step1: {response: {...}}}
        step_results = []
        
        # 创建HTTP客户端,禁用SSL验证
        async with httpx.AsyncClient(
            verify=False,      # 禁用SSL验证
            timeout=30.0,      # 30秒超时
            follow_redirects=True  # 跟随重定向
        ) as client:
            for step in steps:
                step_order = step.get("step_order", 0)
                start_time = datetime.now()
                # 1. 确定 Base URL
                current_base_url = req.base_url.strip() if req.base_url else ""
                if not current_base_url or current_base_url == "http://localhost:8000":
                    if step.get("base_url"):
                        current_base_url = step.get("base_url").strip()

                # 定义预期的步骤数据（即使失败也要记录）
                step_data = {
                    "step_order": step_order,
                    "url": "",
                    "method": step.get("api_method", "GET").upper(),
                    "request_data": step.get("params", {}),
                    "success": False,
                    "status_code": "Error",
                    "extractions": []  # 新增:提取记录
                }
                
                try:
                    # 1. 变量替换与参数准备
                    api_path = step.get('api_path', '')
                    # 强转码路径部分，防止非 ASCII 字符抛出 Invalid non-printable ASCII character
                    safe_path = urllib.parse.quote(api_path.lstrip('/'), safe="/?=&")
                    url = f"{current_base_url.rstrip('/')}/{safe_path}"
                    
                    params = step.get("params", {}).copy()
                    method = step_data["method"]
                    step_data["url"] = url
                    
                    # 处理headers
                    headers = step.get("headers", {}).copy()
                    
                    # 处理参数映射(包括 headers中的变量替换)并记录提取过程
                    extractions = []
                    for mapping in step.get("param_mappings", []):
                        from_step_idx = mapping.get("from_step")
                        from_field = mapping.get("from_field")
                        to_field = mapping.get("to_field")
                        
                        # 初始化提取记录
                        extraction = {
                            "from_step": from_step_idx,
                            "from_field": from_field,
                            "to_field": to_field,
                            "extracted_value": None,
                            "success": False,
                            "error_msg": ""
                        }
                        
                        if from_step_idx is None or to_field is None:
                            extraction["error_msg"] = "参数映射配置不完整"
                            extractions.append(extraction)
                            continue
                        
                        from_data = context.get(f"step_{from_step_idx}", {}).get("response")
                        if isinstance(from_data, dict):
                            field_val = from_data.get(from_field)
                            if field_val:
                                extraction["extracted_value"] = field_val
                                extraction["success"] = True
                                # 支持headers中的变量替换
                                if to_field.startswith("headers."):
                                    header_key = to_field.replace("headers.", "")
                                    headers[header_key] = field_val
                                else:
                                    params[to_field] = field_val
                            else:
                                extraction["error_msg"] = f"字段 {from_field} 不存在"
                        else:
                            extraction["error_msg"] = f"步骤 {from_step_idx} 的响应数据不是字典类型"
                        
                        extractions.append(extraction)
                    
                    step_data["extractions"] = extractions
                    
                    # 处理headers中的变量引用 ${stepX.field}
                    print(f"   原始Headers: {json.dumps(headers, ensure_ascii=False)}")
                    for key, value in list(headers.items()):  # 使用list()避免字典大小改变
                        if isinstance(value, str) and "${" in value:
                            print(f"   处理Header {key}: {value}")
                            # 简单的变量替换
                            import re
                            matches = re.findall(r'\$\{step(\d+)\.(.+?)\}', value)
                            print(f"   找到变量引用: {matches}")
                            for step_idx, field_path in matches:
                                step_data_ref = context.get(f"step_{step_idx}", {}).get("response", {})
                                print(f"   从step_{step_idx}获取数据: {type(step_data_ref)}")
                                # 支持嵌套字段如 data.token
                                field_value = step_data_ref
                                for part in field_path.split('.'):
                                    if isinstance(field_value, dict):
                                        field_value = field_value.get(part)
                                    else:
                                        field_value = None
                                        break
                                print(f"   字段{field_path}的值: {field_value}")
                                if field_value:
                                    value = value.replace(f"${{step{step_idx}.{field_path}}}", str(field_value))
                                    print(f"   替换后: {value}")
                            headers[key] = value
                    print(f"   最终Headers: {json.dumps(headers, ensure_ascii=False)}")

                    step_data["request_data"] = params
                    
                    # 2. 发送请求
                    print(f"🚀 执行步骤 {step_order}: {method} {url}")
                    print(f"   参数: {json.dumps(params, ensure_ascii=False)[:200]}")
                    
                    try:
                        res = await client.request(
                            method, 
                            url, 
                            params=params if method == "GET" else None, 
                            json=params if method != "GET" else None,
                            headers=headers,  # 添加headers
                            timeout=30.0,
                            follow_redirects=True
                        )
                        duration = (datetime.now() - start_time).total_seconds()
                        
                        print(f"   ✅ 响应: {res.status_code} ({duration:.2f}s)")
                        
                        # 3. 记录结果
                        res_content = res.text
                        try:
                            res_json = res.json()
                            res_content = res_json
                        except:
                            pass
                        
                        # 4. 执行断言验证
                        assertions_config = step.get("assertions", [])
                        assertion_results = []
                        
                        # 如果AI没有生成断言,添加默认断言
                        if not assertions_config:
                            assertions_config = [
                                {
                                    "type": "status_code",
                                    "operator": "equals",
                                    "expected_value": 200,
                                    "description": "状态码应为200"
                                },
                                {
                                    "type": "response_time",
                                    "operator": "less_than",
                                    "expected_value": 1000,
                                    "description": "响应时间应小于1秒"
                                }
                            ]
                        
                        # 验证每个断言
                        for assertion in assertions_config:
                            assertion_type = assertion.get("type", "")
                            # 支持expected和expected_value两种字段名
                            expected = assertion.get("expected") or assertion.get("expected_value")
                            description = assertion.get("description", "")
                            
                            result = {
                                "type": assertion_type,
                                "description": description,
                                "expected": expected,
                                "actual": None,
                                "passed": False
                            }
                            
                            try:
                                if assertion_type == "status_code":
                                    result["actual"] = res.status_code
                                    result["passed"] = (res.status_code == expected)
                                
                                elif assertion_type == "response_time":
                                    actual_ms = duration * 1000
                                    result["actual"] = f"{actual_ms:.0f}ms"
                                    result["passed"] = (actual_ms < expected)
                                
                                elif assertion_type == "field_exists":
                                    field = assertion.get("field", "")
                                    if isinstance(res_content, dict):
                                        # 支持嵌套字段,如 "data.user.id"
                                        field_exists = True
                                        current = res_content
                                        for part in field.split("."):
                                            if isinstance(current, dict) and part in current:
                                                current = current[part]
                                            else:
                                                field_exists = False
                                                break
                                        result["actual"] = field_exists
                                        result["passed"] = field_exists
                                    else:
                                        result["actual"] = False
                                        result["passed"] = False
                                
                                elif assertion_type == "field_value":
                                    field = assertion.get("field", "")
                                    if isinstance(res_content, dict):
                                        current = res_content
                                        for part in field.split("."):
                                            if isinstance(current, dict) and part in current:
                                                current = current[part]
                                            else:
                                                current = None
                                                break
                                        result["actual"] = current
                                        result["passed"] = (current == expected)
                                    else:
                                        result["actual"] = None
                                        result["passed"] = False
                                
                                elif assertion_type == "response_contains":
                                    text = assertion.get("text", "")
                                    contains = text in str(res_content)
                                    result["actual"] = contains
                                    result["passed"] = contains
                                
                            except Exception as e:
                                result["error"] = str(e)
                                result["passed"] = False
                            
                            assertion_results.append(result)
                        
                        # 判断步骤是否成功(所有断言都通过)
                        all_assertions_passed = all(a["passed"] for a in assertion_results)
                            
                        step_data.update({
                            "status_code": res.status_code,
                            "duration": duration,
                            "response": res_content,
                            "response_headers": dict(res.headers),  # 新增:响应头
                            "assertions": assertion_results,
                            "success": res.status_code < 400 and all_assertions_passed
                        })
                        context[f"step_{step_order}"] = step_data
                        step_results.append(step_data)
                        
                    except httpx.TimeoutException as e:
                        error_msg = f"请求超时: {repr(e)}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except httpx.ConnectError as e:
                        # ConnectError的str()可能为空,使用repr()获取详细信息
                        error_detail = str(e) if str(e) else repr(e)
                        error_msg = f"连接失败: {error_detail}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except httpx.HTTPStatusError as e:
                        error_msg = f"HTTP错误 {e.response.status_code}: {str(e)}"
                        print(f"   ❌ {error_msg}")
                        step_data["error"] = error_msg
                        step_results.append(step_data)
                    except Exception as e:
                        error_detail = str(e) if str(e) else repr(e)
                        error_msg = f"请求异常: {type(e).__name__}: {error_detail}"
                        print(f"   ❌ {error_msg}")
                        import traceback
                        traceback.print_exc()

                        step_data["error"] = error_msg
                        step_results.append(step_data)
                except Exception as e:
                    error_msg = f"步骤准备异常: {type(e).__name__}: {str(e)}"
                    print(f"❌ 步骤 {step_order} 运行异常: {error_msg}")
                    step_data["error"] = error_msg
                    # 即使出错也返回已准备好的 URL 和 Method，方便前端展示
                    step_results.append(step_data)

        # 4. 保存执行记录并判定总状态
        final_status = "success" if all(s.get("success", False) for s in step_results) else "failed"
        
        # 只有完整场景执行才保存到数据库
        if req.test_case_id:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
                (req.test_case_id, final_status, json.dumps(step_results))
            )
            exec_id = cursor.lastrowid
            conn.commit()
            conn.close()
        else:
            # 单步执行使用临时ID
            exec_id = 0
        
        return {"id": exec_id, "status": final_status, "results": step_results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 导入与列表 (保持原有逻辑) ---

@app.get("/api/v1/projects")
async def list_projects():
    """获取系统中所有项目 ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT project_id FROM apis UNION SELECT DISTINCT project_id FROM scenarios")
    rows = cursor.fetchall()
    conn.close()
    return {"projects": [r[0] for r in rows if r[0]]}

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
            "project_id": r["project_id"],
            "tags": []
        } for r in rows
    ]}

@app.delete("/api/v1/apis/{api_id}")
async def delete_api(api_id: str):
    """删除单个API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE id = ?", (api_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail="API不存在")
        
        return {"success": True, "message": "API删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/apis/project/{project_id}")
async def delete_apis_by_project(project_id: str):
    """批量删除指定项目的所有API"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"success": True, "deleted": deleted_count, "message": f"已删除 {deleted_count} 个API"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/import/postman")
async def import_postman(file: UploadFile = File(...), project_id: str = Form("default-project")):
    """导入Postman Collection文件"""
    import tempfile
    
    try:
        # 1. 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='wb') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 2. 读取并解析Collection
        with open(tmp_path, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        # 3. 解析Collection中的API
        apis = []
        _parse_postman_items(collection.get('item', []), apis, project_id)
        
        # 4. 保存到数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 删除该项目的旧数据
        cursor.execute("DELETE FROM apis WHERE project_id = ?", (project_id,))
        
        # 插入新数据
        for api in apis:
            cursor.execute("""
                INSERT INTO apis (path, method, summary, description, base_url, parameters, request_body, headers, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api['path'],
                api['method'],
                api['name'],
                api.get('description', ''),
                api.get('base_url', ''),
                json.dumps(api.get('parameters', [])),
                json.dumps(api.get('request_body', {})),
                json.dumps(api.get('headers', {})),
                project_id
            ))
        
        conn.commit()
        conn.close()
        
        # 5. 清理临时文件
        os.remove(tmp_path)
        
        return {
            "success": True,
            "indexed": len(apis),
            "total": len(apis),
            "project_id": project_id
        }
        
    except Exception as e:
        print(f"❌ Postman导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e)
        }

def _parse_postman_items(items: List, apis: List, project_id: str, folder_path: str = ""):
    """递归解析Postman Collection项"""
    for item in items:
        if 'request' in item:
            # 这是一个请求
            api = _convert_postman_request(item, folder_path)
            apis.append(api)
        elif 'item' in item:
            # 这是一个文件夹
            new_path = f"{folder_path}/{item['name']}" if folder_path else item['name']
            _parse_postman_items(item['item'], apis, project_id, new_path)

def _convert_postman_request(item: dict, folder_path: str) -> dict:
    """转换Postman请求为标准格式"""
    request = item.get('request', {})
    url = request.get('url', {})
    
    # 处理URL
    if isinstance(url, str):
        path = url
        base_url = ""
    else:
        path = '/' + '/'.join(url.get('path', []))
        # 提取base_url
        protocol = url.get('protocol', 'http')
        host = url.get('host', [])
        if isinstance(host, list):
            base_url = f"{protocol}://{'.'.join(host)}"
        else:
            base_url = f"{protocol}://{host}"
    
    # 解析参数和Headers
    parameters = []
    headers = {}
    
    # Query参数
    if isinstance(url, dict):
        for query in url.get('query', []):
            if not query.get('disabled', False):
                parameters.append({
                    "name": query.get('key'),
                    "in": "query",
                    "type": "string",
                    "required": True,
                    "description": query.get('description', '')
                })
    
    # Header参数 - 单独提取为headers字典
    for header in request.get('header', []):
        if not header.get('disabled', False):
            headers[header.get('key')] = header.get('value', '')
    
    # 解析请求体
    request_body = {}
    body = request.get('body', {})
    if body:
        mode = body.get('mode', 'raw')
        if mode == 'raw':
            try:
                raw_data = json.loads(body.get('raw', '{}'))
                request_body = {"schema": raw_data}
            except:
                request_body = {}
        elif mode == 'formdata':
            request_body = {"schema": {"type": "formdata"}}
    
    return {
        "name": item.get('name', ''),
        "path": path,
        "method": request.get('method', 'GET'),
        "description": item.get('description', ''),
        "base_url": base_url,
        "parameters": parameters,
        "request_body": request_body,
        "headers": headers,
        "tags": [folder_path] if folder_path else []
    }

if __name__ == "__main__":
    print(f"🚀 启动统一后端 (Unified Backend)... 数据库: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)

