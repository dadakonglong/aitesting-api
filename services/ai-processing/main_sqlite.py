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
    test_case_id: int
    environment: str = "test"
    base_url: str = "http://localhost:8000"

@app.post("/api/v1/executions")
async def execute_case(req: ExecutionRequest):
    """链式执行引擎：支持变量动态映射和 HTTP 发送"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM test_cases WHERE id = ?", (req.test_case_id,))
        case = cursor.fetchone()
        if not case: raise HTTPException(status_code=404, detail="用例不存在")
        
        steps = json.loads(case["steps"])
        context = {} # 存储运行时变量，如 {step1: {response: {...}}}
        step_results = []
        
        async with httpx.AsyncClient() as client:
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
                    "status_code": "Error"
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
                    
                    # 处理参数映射
                    for mapping in step.get("param_mappings", []):
                        from_step_idx = mapping.get("from_step")
                        from_field = mapping.get("from_field")
                        to_field = mapping.get("to_field")
                        
                        if from_step_idx is None or to_field is None: continue
                        
                        from_data = context.get(f"step_{from_step_idx}", {}).get("response")
                        if isinstance(from_data, dict):
                            field_val = from_data.get(from_field)
                            if field_val: params[to_field] = field_val

                    step_data["request_data"] = params
                    
                    # 2. 发送请求
                    print(f"🚀 执行步骤 {step_order}: {method} {url}")
                    res = await client.request(
                        method, 
                        url, 
                        params=params if method == "GET" else None, 
                        json=params if method != "GET" else None, 
                        timeout=10.0
                    )
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    # 3. 记录结果
                    res_content = res.text
                    try:
                        res_json = res.json()
                        res_content = res_json
                    except:
                        pass
                        
                    step_data.update({
                        "status_code": res.status_code,
                        "duration": duration,
                        "response": res_content,
                        "success": res.status_code < 400
                    })
                    context[f"step_{step_order}"] = step_data
                    step_results.append(step_data)
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 步骤 {step_order} 运行异常: {error_msg}")
                    step_data["error"] = error_msg
                    # 即使出错也返回已准备好的 URL 和 Method，方便前端展示
                    step_results.append(step_data)

        # 4. 保存执行记录并判定总状态
        final_status = "success" if all(s.get("success", False) for s in step_results) else "failed"
        
        cursor.execute(
            "INSERT INTO executions (test_case_id, status, results) VALUES (?, ?, ?)",
            (req.test_case_id, final_status, json.dumps(step_results))
        )
        exec_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
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

if __name__ == "__main__":
    print(f"🚀 启动统一后端 (Unified Backend)... 数据库: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
